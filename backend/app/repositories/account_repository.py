"""Financial account persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus, AccountType
from app.models.financial_account import FinancialAccount


async def create_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    account_type: AccountType,
    currency: str,
    opening_balance: Decimal,
) -> FinancialAccount:
    account = FinancialAccount(
        user_id=user_id,
        name=name,
        account_type=account_type,
        currency=currency,
        opening_balance=opening_balance,
        current_balance=opening_balance,
        status=AccountStatus.ACTIVE,
    )
    session.add(account)
    await session.flush()
    return account


async def list_accounts_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    status: AccountStatus | None,
    offset: int,
    limit: int,
) -> tuple[list[FinancialAccount], int]:
    filters = [FinancialAccount.user_id == user_id]
    if status is not None:
        filters.append(FinancialAccount.status == status)

    total = await session.scalar(
        select(func.count()).select_from(FinancialAccount).where(*filters),
    )
    result = await session.execute(
        select(FinancialAccount)
        .where(*filters)
        .order_by(FinancialAccount.name.asc(), FinancialAccount.id.asc())
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)


async def archive_account(session: AsyncSession, account: FinancialAccount) -> None:
    account.status = AccountStatus.ARCHIVED
    account.archived_at = datetime.now(UTC)
    await session.flush()
