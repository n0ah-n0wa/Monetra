"""Transfer service."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.domain.transactions import apply_balance_delta
from app.domain.transfers import (
    assert_sufficient_balance,
    resolve_transfer_amounts,
)
from app.models.enums import AccountStatus, AuditAction
from app.models.financial_account import FinancialAccount
from app.models.transfer import Transfer
from app.repositories import transaction_repository as transaction_repo
from app.repositories import transfer_repository as transfer_repo
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)
from app.schemas.transfers import TransferCreateRequest
from app.services import audit_service


def _transfer_matches_request(
    transfer: Transfer,
    payload: TransferCreateRequest,
    *,
    source_amount: Decimal,
    destination_amount: Decimal,
    exchange_rate: Decimal | None,
) -> bool:
    description = payload.description.strip() if payload.description else None
    return (
        transfer.source_account_id == payload.source_account_id
        and transfer.destination_account_id == payload.destination_account_id
        and transfer.source_amount == source_amount
        and transfer.destination_amount == destination_amount
        and transfer.exchange_rate == exchange_rate
        and transfer.transaction_date == payload.transaction_date
        and (transfer.description or None) == description
    )


def _require_active_account(account: FinancialAccount, *, role: str) -> None:
    if account.status == AccountStatus.ARCHIVED:
        raise ValidationAppError(
            code="ACCOUNT_ARCHIVED",
            message=f"The {role} account cannot be used for transfers.",
        )


async def _find_idempotent_transfer(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: TransferCreateRequest,
    source_amount: Decimal,
    destination_amount: Decimal,
    exchange_rate: Decimal | None,
) -> Transfer | None:
    if not payload.idempotency_key:
        return None
    existing = await transfer_repo.get_transfer_by_idempotency_key(
        session,
        user_id=user_id,
        idempotency_key=payload.idempotency_key,
    )
    if existing is None:
        return None
    if _transfer_matches_request(
        existing,
        payload,
        source_amount=source_amount,
        destination_amount=destination_amount,
        exchange_rate=exchange_rate,
    ):
        return existing
    raise ConflictError(
        code="IDEMPOTENCY_KEY_CONFLICT",
        message="The idempotency key was already used with a different request.",
    )


async def create_transfer(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: TransferCreateRequest,
) -> tuple[Transfer, bool]:
    """Create a transfer. Returns the transfer and whether it was newly created."""
    if payload.source_account_id == payload.destination_account_id:
        raise ValidationAppError(
            code="SAME_ACCOUNT_TRANSFER",
            message="Source and destination accounts must be different.",
        )

    locked = await transaction_repo.lock_accounts_for_update(
        session,
        user_id=user_id,
        account_ids={payload.source_account_id, payload.destination_account_id},
    )
    source_account = locked.get(payload.source_account_id)
    destination_account = locked.get(payload.destination_account_id)
    if source_account is None or destination_account is None:
        raise NotFoundError(
            code="ACCOUNT_NOT_FOUND",
            message="Financial account was not found.",
        )

    _require_active_account(source_account, role="source")
    _require_active_account(destination_account, role="destination")

    source_amount, destination_amount, exchange_rate = resolve_transfer_amounts(
        source_currency=source_account.currency,
        destination_currency=destination_account.currency,
        source_amount=payload.source_amount,
        destination_amount=payload.destination_amount,
        exchange_rate=payload.exchange_rate,
    )

    existing = await _find_idempotent_transfer(
        session,
        user_id=user_id,
        payload=payload,
        source_amount=source_amount,
        destination_amount=destination_amount,
        exchange_rate=exchange_rate,
    )
    if existing is not None:
        return existing, False

    assert_sufficient_balance(source_account.current_balance, source_amount)

    source_account.current_balance = apply_balance_delta(
        source_account.current_balance,
        -source_amount,
    )
    destination_account.current_balance = apply_balance_delta(
        destination_account.current_balance,
        destination_amount,
    )

    try:
        transfer = await transfer_repo.create_transfer(
            session,
            user_id=user_id,
            source_account_id=source_account.id,
            destination_account_id=destination_account.id,
            source_amount=source_amount,
            source_currency=source_account.currency,
            destination_amount=destination_amount,
            destination_currency=destination_account.currency,
            exchange_rate=exchange_rate,
            transaction_date=payload.transaction_date,
            description=payload.description.strip() if payload.description else None,
            idempotency_key=payload.idempotency_key,
        )
        await audit_service.record_event(
            session,
            actor_id=user_id,
            action=AuditAction.CREATED,
            entity_type=audit_service.ENTITY_TRANSFER,
            entity_id=transfer.id,
            metadata={
                "source_account_id": str(transfer.source_account_id),
                "destination_account_id": str(transfer.destination_account_id),
                "source_amount": transfer.source_amount,
                "source_currency": transfer.source_currency,
                "destination_amount": transfer.destination_amount,
                "destination_currency": transfer.destination_currency,
                "exchange_rate": transfer.exchange_rate,
                "transaction_date": transfer.transaction_date,
            },
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raced = await _find_idempotent_transfer(
            session,
            user_id=user_id,
            payload=payload,
            source_amount=source_amount,
            destination_amount=destination_amount,
            exchange_rate=exchange_rate,
        )
        if raced is not None:
            return raced, False
        raise ConflictError(
            code="TRANSFER_CONFLICT",
            message="The transfer could not be created due to a conflict.",
        ) from exc

    await session.refresh(transfer)
    return transfer, True


async def get_transfer(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    transfer_id: uuid.UUID,
) -> Transfer:
    transfer = await transfer_repo.get_transfer_by_id(
        session,
        user_id=user_id,
        transfer_id=transfer_id,
    )
    if transfer is None:
        raise NotFoundError(
            code="TRANSFER_NOT_FOUND",
            message="Transfer was not found.",
        )
    return transfer


async def list_transfers(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    page: int,
    page_size: int,
) -> PaginatedResponse[Transfer]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size,
        max_page_size=settings.api_max_page_size,
    )
    transfers, total = await transfer_repo.list_transfers_for_user(
        session,
        user_id=user_id,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=transfers,
        page=max(page, 1),
        page_size=limit,
        total_items=total,
    )
