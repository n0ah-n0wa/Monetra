"""Transaction service."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.domain.currency import normalize_currency
from app.domain.transactions import (
    apply_balance_delta,
    category_supports_transaction_type,
    compute_update_balance_adjustments,
    normalize_money,
    signed_transaction_amount,
    validate_positive_amount,
)
from app.models.category import Category
from app.models.enums import AccountStatus, CategoryStatus, TransactionType
from app.models.financial_account import FinancialAccount
from app.models.transaction import Transaction
from app.repositories import transaction_repository as transaction_repo
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)
from app.schemas.transactions import (
    SortOrder,
    TransactionCreateRequest,
    TransactionSortField,
    TransactionUpdateRequest,
)
from app.services import ownership


def _is_balance_affecting_update(
    transaction: Transaction,
    payload: TransactionUpdateRequest,
    *,
    new_account_id: uuid.UUID,
    new_type: TransactionType,
    new_amount: Decimal,
) -> bool:
    return (
        new_account_id != transaction.account_id
        or new_type != transaction.transaction_type
        or new_amount != transaction.amount
    )


async def _require_active_account(account: FinancialAccount) -> None:
    if account.status == AccountStatus.ARCHIVED:
        raise ValidationAppError(
            code="ACCOUNT_ARCHIVED",
            message="Archived accounts cannot receive transactions.",
        )


async def _validate_category_for_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    transaction_type: TransactionType,
) -> Category:
    category = await ownership.get_accessible_category(
        session,
        user_id=user_id,
        category_id=category_id,
    )
    if category.status == CategoryStatus.ARCHIVED:
        raise ValidationAppError(
            code="CATEGORY_ARCHIVED",
            message="Archived categories cannot be used for transactions.",
        )
    if not category_supports_transaction_type(
        category.category_type,
        transaction_type,
    ):
        raise ValidationAppError(
            code="CATEGORY_TYPE_MISMATCH",
            message="Category type does not match the transaction type.",
        )
    return category


async def _lock_and_apply_balance_adjustments(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    adjustments: dict[uuid.UUID, Decimal],
) -> None:
    if not adjustments:
        return

    account_ids = {account_id for account_id, delta in adjustments.items() if delta}
    locked = await transaction_repo.lock_accounts_for_update(
        session,
        user_id=user_id,
        account_ids=account_ids,
    )
    if len(locked) != len(account_ids):
        raise NotFoundError(
            code="ACCOUNT_NOT_FOUND",
            message="Financial account was not found.",
        )

    for account_id in sorted(account_ids):
        delta = adjustments[account_id]
        if delta == Decimal("0"):
            continue
        account = locked[account_id]
        account.current_balance = apply_balance_delta(account.current_balance, delta)


async def create_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: TransactionCreateRequest,
) -> Transaction:
    amount = validate_positive_amount(payload.amount)
    await _validate_category_for_transaction(
        session,
        user_id=user_id,
        category_id=payload.category_id,
        transaction_type=payload.transaction_type,
    )

    locked = await transaction_repo.lock_accounts_for_update(
        session,
        user_id=user_id,
        account_ids={payload.account_id},
    )
    account = locked.get(payload.account_id)
    if account is None:
        raise NotFoundError(
            code="ACCOUNT_NOT_FOUND",
            message="Financial account was not found.",
        )
    await _require_active_account(account)

    delta = signed_transaction_amount(payload.transaction_type, amount)
    account.current_balance = apply_balance_delta(account.current_balance, delta)

    transaction = await transaction_repo.create_transaction(
        session,
        user_id=user_id,
        account_id=account.id,
        category_id=payload.category_id,
        transaction_type=payload.transaction_type,
        amount=amount,
        currency=account.currency,
        description=payload.description.strip(),
        transaction_date=payload.transaction_date,
        notes=payload.notes,
    )
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def get_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> Transaction:
    transaction = await transaction_repo.get_active_transaction(
        session,
        user_id=user_id,
        transaction_id=transaction_id,
    )
    if transaction is None:
        raise NotFoundError(
            code="TRANSACTION_NOT_FOUND",
            message="Transaction was not found.",
        )
    return transaction


async def list_transactions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    account_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    transaction_type: TransactionType | None,
    date_from: date | None,
    date_to: date | None,
    amount_min: Decimal | None,
    amount_max: Decimal | None,
    currency: str | None,
    description: str | None,
    sort_by: TransactionSortField,
    sort_order: SortOrder,
    page: int,
    page_size: int,
) -> PaginatedResponse[Transaction]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValidationAppError(
            code="INVALID_DATE_RANGE",
            message="date_from must be on or before date_to.",
        )
    if amount_min is not None:
        amount_min = normalize_money(amount_min)
        if amount_min < Decimal("0"):
            raise ValidationAppError(
                code="INVALID_AMOUNT_RANGE",
                message="amount_min must be greater than or equal to zero.",
            )
    if amount_max is not None:
        amount_max = normalize_money(amount_max)
        if amount_max < Decimal("0"):
            raise ValidationAppError(
                code="INVALID_AMOUNT_RANGE",
                message="amount_max must be greater than or equal to zero.",
            )
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise ValidationAppError(
            code="INVALID_AMOUNT_RANGE",
            message="amount_min must be less than or equal to amount_max.",
        )
    if currency is not None:
        currency = normalize_currency(currency)

    if account_id is not None:
        await ownership.get_owned_account(
            session,
            user_id=user_id,
            account_id=account_id,
        )
    if category_id is not None:
        await ownership.get_accessible_category(
            session,
            user_id=user_id,
            category_id=category_id,
        )

    offset, limit = pagination_params(
        page=page,
        page_size=page_size,
        max_page_size=settings.api_max_page_size,
    )
    transactions, total = await transaction_repo.list_transactions_for_user(
        session,
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        currency=currency,
        description=description.strip() if description else None,
        sort_by=sort_by,
        sort_order=sort_order,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=transactions,
        page=max(page, 1),
        page_size=limit,
        total_items=total,
    )


async def update_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    payload: TransactionUpdateRequest,
) -> Transaction:
    if (
        payload.account_id is None
        and payload.category_id is None
        and payload.transaction_type is None
        and payload.amount is None
        and payload.description is None
        and payload.transaction_date is None
        and payload.notes is None
    ):
        raise ValidationAppError(
            code="VALIDATION_ERROR",
            message="At least one field must be provided for update.",
        )

    transaction = await transaction_repo.get_active_transaction_for_update(
        session,
        user_id=user_id,
        transaction_id=transaction_id,
    )
    if transaction is None:
        raise NotFoundError(
            code="TRANSACTION_NOT_FOUND",
            message="Transaction was not found.",
        )

    new_account_id = payload.account_id or transaction.account_id
    new_category_id = payload.category_id or transaction.category_id
    new_type = payload.transaction_type or transaction.transaction_type
    new_amount = (
        validate_positive_amount(payload.amount)
        if payload.amount is not None
        else transaction.amount
    )
    new_description = (
        payload.description.strip()
        if payload.description is not None
        else transaction.description
    )
    new_date = (
        payload.transaction_date
        if payload.transaction_date is not None
        else transaction.transaction_date
    )
    new_notes = payload.notes if payload.notes is not None else transaction.notes

    balance_affecting = _is_balance_affecting_update(
        transaction,
        payload,
        new_account_id=new_account_id,
        new_type=new_type,
        new_amount=new_amount,
    )

    if payload.category_id is not None or payload.transaction_type is not None:
        await _validate_category_for_transaction(
            session,
            user_id=user_id,
            category_id=new_category_id,
            transaction_type=new_type,
        )

    new_currency = transaction.currency
    if balance_affecting:
        adjustments = compute_update_balance_adjustments(
            old_account_id=transaction.account_id,
            new_account_id=new_account_id,
            old_type=transaction.transaction_type,
            old_amount=transaction.amount,
            new_type=new_type,
            new_amount=new_amount,
        )
        account_ids = {account_id for account_id, delta in adjustments.items() if delta}
        locked = await transaction_repo.lock_accounts_for_update(
            session,
            user_id=user_id,
            account_ids=account_ids,
        )
        if len(locked) != len(account_ids):
            raise NotFoundError(
                code="ACCOUNT_NOT_FOUND",
                message="Financial account was not found.",
            )
        new_account = locked[new_account_id]
        await _require_active_account(new_account)
        new_currency = new_account.currency

        for account_id in sorted(account_ids):
            delta = adjustments[account_id]
            if delta == Decimal("0"):
                continue
            locked[account_id].current_balance = apply_balance_delta(
                locked[account_id].current_balance,
                delta,
            )

    transaction.account_id = new_account_id
    transaction.category_id = new_category_id
    transaction.transaction_type = new_type
    transaction.amount = new_amount
    transaction.currency = new_currency
    transaction.description = new_description
    transaction.transaction_date = new_date
    transaction.notes = new_notes

    await session.commit()
    await session.refresh(transaction)
    return transaction


async def delete_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> None:
    transaction = await transaction_repo.get_active_transaction_for_update(
        session,
        user_id=user_id,
        transaction_id=transaction_id,
    )
    if transaction is None:
        raise NotFoundError(
            code="TRANSACTION_NOT_FOUND",
            message="Transaction was not found.",
        )

    delta = -signed_transaction_amount(
        transaction.transaction_type,
        transaction.amount,
    )
    await _lock_and_apply_balance_adjustments(
        session,
        user_id=user_id,
        adjustments={transaction.account_id: delta},
    )
    await transaction_repo.soft_delete_transaction(session, transaction)
    await session.commit()
