"""Financial account service."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, ValidationAppError
from app.domain.transactions import normalize_money
from app.models.enums import AccountStatus
from app.models.financial_account import FinancialAccount
from app.repositories import account_repository as account_repo
from app.schemas.accounts import AccountCreateRequest, AccountUpdateRequest
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)
from app.services import ownership


async def create_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: AccountCreateRequest,
) -> FinancialAccount:
    try:
        account = await account_repo.create_account(
            session,
            user_id=user_id,
            name=payload.name.strip(),
            account_type=payload.account_type,
            currency=payload.currency,
            opening_balance=normalize_money(payload.opening_balance),
        )
        await session.commit()
        return account
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            code="ACCOUNT_NAME_CONFLICT",
            message="An account with this name already exists.",
        ) from exc


async def list_accounts(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    status: AccountStatus | None,
    page: int,
    page_size: int,
) -> PaginatedResponse[FinancialAccount]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size,
        max_page_size=settings.api_max_page_size,
    )
    accounts, total = await account_repo.list_accounts_for_user(
        session,
        user_id=user_id,
        status=status,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=accounts,
        page=max(page, 1),
        page_size=limit,
        total_items=total,
    )


async def get_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> FinancialAccount:
    return await ownership.get_owned_account(
        session,
        user_id=user_id,
        account_id=account_id,
    )


async def update_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    payload: AccountUpdateRequest,
) -> FinancialAccount:
    if payload.name is None and payload.account_type is None:
        raise ValidationAppError(
            code="VALIDATION_ERROR",
            message="At least one field must be provided for update.",
        )

    account = await ownership.get_owned_account(
        session,
        user_id=user_id,
        account_id=account_id,
    )
    if account.status == AccountStatus.ARCHIVED:
        raise ValidationAppError(
            code="ACCOUNT_ARCHIVED",
            message="Archived accounts cannot be modified.",
        )

    if payload.name is not None:
        account.name = payload.name.strip()
    if payload.account_type is not None:
        account.account_type = payload.account_type

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            code="ACCOUNT_NAME_CONFLICT",
            message="An account with this name already exists.",
        ) from exc
    await session.refresh(account)
    return account


async def archive_account(
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
    if account.status != AccountStatus.ARCHIVED:
        await account_repo.archive_account(session, account)
        await session.commit()
        await session.refresh(account)
    return account
