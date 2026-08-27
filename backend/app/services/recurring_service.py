"""Recurring transaction service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.domain.notifications import NotificationProvider
from app.domain.recurring import (
    advance_execution_date,
    advance_next_execution_pointer,
    due_execution_dates,
    initial_next_execution_date,
    is_execution_due,
    recompute_next_execution_date,
    validate_date_range,
)
from app.domain.transactions import (
    apply_balance_delta,
    category_supports_transaction_type,
    signed_transaction_amount,
    validate_positive_amount,
)
from app.models.enums import AccountStatus, CategoryStatus, TransactionType
from app.models.financial_account import FinancialAccount
from app.models.recurring_transaction import RecurringTransaction
from app.models.recurring_transaction_execution import RecurringTransactionExecution
from app.repositories import recurring_repository as recurring_repo
from app.repositories import transaction_repository as transaction_repo
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)
from app.schemas.recurring_transactions import (
    ProcessDueRecurringResponse,
    RecurringExecutionResult,
    RecurringTransactionCreateRequest,
    RecurringTransactionUpdateRequest,
)
from app.services import notification_service, ownership


async def _validate_category_for_recurring(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    transaction_type: TransactionType,
) -> None:
    category = await ownership.get_accessible_category(
        session,
        user_id=user_id,
        category_id=category_id,
    )
    if category.status == CategoryStatus.ARCHIVED:
        raise ValidationAppError(
            code="CATEGORY_ARCHIVED",
            message="Archived categories cannot be used for recurring transactions.",
        )
    if not category_supports_transaction_type(
        category.category_type,
        transaction_type,
    ):
        raise ValidationAppError(
            code="CATEGORY_TYPE_MISMATCH",
            message="Category type does not match the transaction type.",
        )


async def _require_active_account(account: FinancialAccount) -> None:
    if account.status == AccountStatus.ARCHIVED:
        raise ValidationAppError(
            code="ACCOUNT_ARCHIVED",
            message="Archived accounts cannot be used for recurring transactions.",
        )


async def _resolve_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> FinancialAccount:
    account = await ownership.get_owned_account(
        session,
        user_id=user_id,
        account_id=account_id,
    )
    await _require_active_account(account)
    return account


def _deactivate_if_past_end(recurring: RecurringTransaction) -> None:
    if recurring.end_date is None:
        return
    if recurring.next_execution_date > recurring.end_date:
        recurring.is_active = False


async def create_recurring_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: RecurringTransactionCreateRequest,
) -> RecurringTransaction:
    amount = validate_positive_amount(payload.amount)
    await _validate_category_for_recurring(
        session,
        user_id=user_id,
        category_id=payload.category_id,
        transaction_type=payload.transaction_type,
    )
    account = await _resolve_account(
        session,
        user_id=user_id,
        account_id=payload.account_id,
    )

    next_execution_date = initial_next_execution_date(payload.start_date)
    if not is_execution_due(next_execution_date, end_date=payload.end_date):
        raise ValidationAppError(
            code="INVALID_DATE_RANGE",
            message="start_date must be on or before end_date.",
        )

    recurring = await recurring_repo.create_recurring_transaction(
        session,
        user_id=user_id,
        account_id=account.id,
        category_id=payload.category_id,
        transaction_type=payload.transaction_type,
        amount=amount,
        currency=account.currency,
        description=payload.description.strip(),
        frequency=payload.frequency,
        start_date=payload.start_date,
        end_date=payload.end_date,
        next_execution_date=next_execution_date,
    )
    await session.commit()
    await session.refresh(recurring)
    return recurring


async def get_recurring_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
) -> RecurringTransaction:
    recurring = await recurring_repo.get_recurring_transaction(
        session,
        user_id=user_id,
        recurring_id=recurring_id,
    )
    if recurring is None:
        raise NotFoundError(
            code="RECURRING_TRANSACTION_NOT_FOUND",
            message="Recurring transaction was not found.",
        )
    return recurring


async def list_recurring_transactions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    is_active: bool | None,
    page: int,
    page_size: int,
) -> PaginatedResponse[RecurringTransaction]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size,
        max_page_size=settings.api_max_page_size,
    )
    items, total = await recurring_repo.list_recurring_transactions_for_user(
        session,
        user_id=user_id,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=items,
        page=max(page, 1),
        page_size=limit,
        total_items=total,
    )


async def update_recurring_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
    payload: RecurringTransactionUpdateRequest,
) -> RecurringTransaction:
    if (
        payload.account_id is None
        and payload.category_id is None
        and payload.transaction_type is None
        and payload.amount is None
        and payload.description is None
        and payload.frequency is None
        and payload.start_date is None
        and payload.end_date is None
        and payload.is_active is None
    ):
        raise ValidationAppError(
            code="VALIDATION_ERROR",
            message="At least one field must be provided for update.",
        )

    recurring = await recurring_repo.get_recurring_transaction_for_update(
        session,
        user_id=user_id,
        recurring_id=recurring_id,
    )
    if recurring is None:
        raise NotFoundError(
            code="RECURRING_TRANSACTION_NOT_FOUND",
            message="Recurring transaction was not found.",
        )

    new_account_id = payload.account_id or recurring.account_id
    new_category_id = payload.category_id or recurring.category_id
    new_type = payload.transaction_type or recurring.transaction_type
    new_amount = (
        validate_positive_amount(payload.amount)
        if payload.amount is not None
        else recurring.amount
    )
    new_description = (
        payload.description.strip()
        if payload.description is not None
        else recurring.description
    )
    new_frequency = payload.frequency or recurring.frequency
    new_start_date = payload.start_date or recurring.start_date
    if "end_date" in payload.model_fields_set:
        new_end_date = payload.end_date
    else:
        new_end_date = recurring.end_date

    validate_date_range(start_date=new_start_date, end_date=new_end_date)

    if payload.category_id is not None or payload.transaction_type is not None:
        await _validate_category_for_recurring(
            session,
            user_id=user_id,
            category_id=new_category_id,
            transaction_type=new_type,
        )

    if payload.account_id is not None:
        account = await _resolve_account(
            session,
            user_id=user_id,
            account_id=new_account_id,
        )
        recurring.currency = account.currency

    schedule_changed = (
        payload.frequency is not None
        or payload.start_date is not None
        or payload.end_date is not None
    )

    recurring.account_id = new_account_id
    recurring.category_id = new_category_id
    recurring.transaction_type = new_type
    recurring.amount = new_amount
    recurring.description = new_description
    recurring.frequency = new_frequency
    recurring.start_date = new_start_date
    recurring.end_date = new_end_date

    if payload.is_active is not None:
        recurring.is_active = payload.is_active

    if schedule_changed and recurring.is_active:
        executed_dates = await recurring_repo.list_executed_dates(
            session,
            recurring_id=recurring.id,
        )
        today = datetime.now(UTC).date()
        next_date = recompute_next_execution_date(
            start_date=new_start_date,
            frequency=new_frequency,
            end_date=new_end_date,
            as_of_date=today,
            executed_dates=executed_dates,
        )
        if next_date is None:
            recurring.is_active = False
        else:
            recurring.next_execution_date = next_date

    _deactivate_if_past_end(recurring)

    await session.commit()
    await session.refresh(recurring)
    return recurring


async def archive_recurring_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
) -> RecurringTransaction:
    recurring = await recurring_repo.get_recurring_transaction_for_update(
        session,
        user_id=user_id,
        recurring_id=recurring_id,
    )
    if recurring is None:
        raise NotFoundError(
            code="RECURRING_TRANSACTION_NOT_FOUND",
            message="Recurring transaction was not found.",
        )
    recurring.is_active = False
    await session.commit()
    await session.refresh(recurring)
    return recurring


async def _execute_recurring_on_date(
    session: AsyncSession,
    *,
    recurring: RecurringTransaction,
    execution_date: date,
    provider: NotificationProvider | None = None,
) -> tuple[uuid.UUID, bool]:
    """Execute one schedule date. Returns transaction id and whether it was created."""
    execution = await recurring_repo.get_execution_for_update(
        session,
        recurring_id=recurring.id,
        execution_date=execution_date,
    )
    if execution is not None and execution.transaction_id is not None:
        return execution.transaction_id, False

    if execution is None:
        session.add(
            RecurringTransactionExecution(
                recurring_transaction_id=recurring.id,
                execution_date=execution_date,
                transaction_id=None,
            ),
        )
        try:
            await session.flush()
        except IntegrityError:
            execution = await recurring_repo.get_execution_for_update(
                session,
                recurring_id=recurring.id,
                execution_date=execution_date,
            )
            if execution is None:
                raise
            if execution.transaction_id is not None:
                return execution.transaction_id, False
        else:
            execution = await recurring_repo.get_execution_for_update(
                session,
                recurring_id=recurring.id,
                execution_date=execution_date,
            )

    if execution is None:
        raise ConflictError(
            code="RECURRING_EXECUTION_CONFLICT",
            message="The recurring execution could not be claimed.",
        )
    if execution.transaction_id is not None:
        return execution.transaction_id, False

    locked = await transaction_repo.lock_accounts_for_update(
        session,
        user_id=recurring.user_id,
        account_ids={recurring.account_id},
    )
    account = locked.get(recurring.account_id)
    if account is None:
        raise NotFoundError(
            code="ACCOUNT_NOT_FOUND",
            message="Financial account was not found.",
        )
    await _require_active_account(account)

    delta = signed_transaction_amount(recurring.transaction_type, recurring.amount)
    account.current_balance = apply_balance_delta(account.current_balance, delta)

    transaction = await transaction_repo.create_transaction(
        session,
        user_id=recurring.user_id,
        account_id=recurring.account_id,
        category_id=recurring.category_id,
        transaction_type=recurring.transaction_type,
        amount=recurring.amount,
        currency=recurring.currency,
        description=recurring.description,
        transaction_date=execution_date,
        notes=None,
    )

    execution.transaction_id = transaction.id
    await session.flush()
    await notification_service.notify_recurring_executed(
        session,
        user_id=recurring.user_id,
        recurring_id=recurring.id,
        transaction_id=transaction.id,
        execution_date=execution_date,
        description=recurring.description,
        provider=provider,
    )
    if recurring.transaction_type == TransactionType.EXPENSE:
        await notification_service.evaluate_budgets_after_expense(
            session,
            user_id=recurring.user_id,
            as_of_date=execution_date,
            provider=provider,
        )
    return transaction.id, True


async def _process_recurring_definition(
    session: AsyncSession,
    *,
    recurring: RecurringTransaction,
    as_of_date: date,
    provider: NotificationProvider | None = None,
) -> list[RecurringExecutionResult]:
    if not recurring.is_active:
        return []

    executed_dates = await recurring_repo.list_executed_dates(
        session,
        recurring_id=recurring.id,
    )
    dates_to_run = due_execution_dates(
        next_execution_date=recurring.next_execution_date,
        frequency=recurring.frequency,
        start_date=recurring.start_date,
        end_date=recurring.end_date,
        as_of_date=as_of_date,
        executed_dates=executed_dates,
    )

    results: list[RecurringExecutionResult] = []
    for execution_date in dates_to_run:
        transaction_id, created = await _execute_recurring_on_date(
            session,
            recurring=recurring,
            execution_date=execution_date,
            provider=provider,
        )
        results.append(
            RecurringExecutionResult(
                recurring_transaction_id=str(recurring.id),
                execution_date=execution_date,
                transaction_id=str(transaction_id),
                created=created,
            ),
        )
        recurring.next_execution_date = advance_execution_date(
            execution_date,
            recurring.frequency,
            start_date=recurring.start_date,
        )
        _deactivate_if_past_end(recurring)
        if not recurring.is_active:
            break

    if not dates_to_run:
        synced = advance_next_execution_pointer(
            next_execution_date=recurring.next_execution_date,
            frequency=recurring.frequency,
            start_date=recurring.start_date,
            end_date=recurring.end_date,
            as_of_date=as_of_date,
            executed_dates=executed_dates,
        )
        if synced is None:
            recurring.is_active = False
        else:
            recurring.next_execution_date = synced
        _deactivate_if_past_end(recurring)

    return results


async def process_due_recurring_transactions_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of_date: date | None = None,
    provider: NotificationProvider | None = None,
) -> ProcessDueRecurringResponse:
    """Process all due recurring definitions for one user (scheduler entry point)."""
    effective_date = as_of_date or datetime.now(UTC).date()
    due_items = await recurring_repo.list_due_recurring_transactions_for_user(
        session,
        user_id=user_id,
        as_of_date=effective_date,
    )

    executions: list[RecurringExecutionResult] = []
    for recurring in due_items:
        executions.extend(
            await _process_recurring_definition(
                session,
                recurring=recurring,
                as_of_date=effective_date,
                provider=provider,
            ),
        )

    await session.commit()
    return ProcessDueRecurringResponse(
        as_of_date=effective_date,
        executions=executions,
    )


async def process_due_recurring_transactions(
    session: AsyncSession,
    *,
    as_of_date: date | None = None,
    provider: NotificationProvider | None = None,
) -> ProcessDueRecurringResponse:
    """Process all due recurring definitions across users (background worker hook)."""
    effective_date = as_of_date or datetime.now(UTC).date()
    due_items = await recurring_repo.list_due_recurring_transactions(
        session,
        as_of_date=effective_date,
    )

    executions: list[RecurringExecutionResult] = []
    for recurring in due_items:
        executions.extend(
            await _process_recurring_definition(
                session,
                recurring=recurring,
                as_of_date=effective_date,
                provider=provider,
            ),
        )

    await session.commit()
    return ProcessDueRecurringResponse(
        as_of_date=effective_date,
        executions=executions,
    )
