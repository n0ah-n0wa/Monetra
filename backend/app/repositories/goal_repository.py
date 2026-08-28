"""Financial goal persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.transactions import normalize_money
from app.models.enums import GoalStatus, TransactionType
from app.models.financial_goal import FinancialGoal
from app.models.transaction import Transaction


async def create_goal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    target_amount: Decimal,
    current_amount: Decimal,
    currency: str,
    target_date: date | None,
    linked_account_id: uuid.UUID | None,
    status: GoalStatus,
) -> FinancialGoal:
    goal = FinancialGoal(
        user_id=user_id,
        name=name,
        target_amount=target_amount,
        current_amount=current_amount,
        currency=currency,
        target_date=target_date,
        linked_account_id=linked_account_id,
        status=status,
    )
    session.add(goal)
    await session.flush()
    return goal


async def get_goal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
) -> FinancialGoal | None:
    result = await session.execute(
        select(FinancialGoal)
        .options(selectinload(FinancialGoal.linked_account))
        .where(
            FinancialGoal.id == goal_id,
            FinancialGoal.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def list_goals_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    status: GoalStatus | None,
    include_archived: bool,
    offset: int,
    limit: int,
) -> tuple[list[FinancialGoal], int]:
    filters = [FinancialGoal.user_id == user_id]
    if status is not None:
        filters.append(FinancialGoal.status == status)
    if not include_archived:
        filters.append(FinancialGoal.archived_at.is_(None))

    total = await session.scalar(
        select(func.count()).select_from(FinancialGoal).where(*filters),
    )
    result = await session.execute(
        select(FinancialGoal)
        .options(selectinload(FinancialGoal.linked_account))
        .where(*filters)
        .order_by(
            FinancialGoal.target_date.asc().nulls_last(), FinancialGoal.name.asc()
        )
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)


async def list_active_goals_linked_to_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> list[FinancialGoal]:
    result = await session.execute(
        select(FinancialGoal).where(
            FinancialGoal.user_id == user_id,
            FinancialGoal.linked_account_id == account_id,
            FinancialGoal.archived_at.is_(None),
        ),
    )
    return list(result.scalars().all())


async def archive_goal(session: AsyncSession, goal: FinancialGoal) -> None:
    goal.status = GoalStatus.ARCHIVED
    goal.archived_at = datetime.now(UTC)
    await session.flush()


async def sum_daily_net_contributions_for_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    currency: str,
    start_date: date,
    end_date: date,
) -> dict[date, Decimal]:
    """Return daily net income minus expense totals for contribution history."""
    result = await session.execute(
        select(
            Transaction.transaction_date,
            Transaction.transaction_type,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.account_id == account_id,
            Transaction.currency == currency,
            Transaction.deleted_at.is_(None),
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .group_by(Transaction.transaction_date, Transaction.transaction_type)
    )
    daily: dict[date, Decimal] = {}
    for tx_date, tx_type, total in result.all():
        amount = Decimal(total or 0)
        signed = amount if tx_type == TransactionType.INCOME else -amount
        daily[tx_date] = normalize_money(daily.get(tx_date, Decimal("0")) + signed)
    return daily
