"""Budget persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.budget import Budget, budget_categories
from app.models.enums import BudgetPeriod, BudgetScope, TransactionType
from app.models.transaction import Transaction


async def create_budget(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    amount: Decimal,
    currency: str,
    period: BudgetPeriod,
    scope: BudgetScope,
    start_date: date,
    end_date: date | None,
    warning_threshold_percent: int,
    category_ids: list[uuid.UUID],
) -> Budget:
    budget = Budget(
        user_id=user_id,
        name=name.strip(),
        amount=amount,
        currency=currency,
        period=period,
        scope=scope,
        start_date=start_date,
        end_date=end_date,
        warning_threshold_percent=warning_threshold_percent,
    )
    session.add(budget)
    await session.flush()

    if category_ids:
        await session.execute(
            insert(budget_categories),
            [
                {"budget_id": budget.id, "category_id": category_id}
                for category_id in category_ids
            ],
        )
        await session.flush()

    return budget


async def get_budget(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> Budget | None:
    result = await session.execute(
        select(Budget)
        .options(selectinload(Budget.categories))
        .where(
            Budget.id == budget_id,
            Budget.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def list_budgets_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    include_archived: bool,
    offset: int,
    limit: int,
) -> tuple[list[Budget], int]:
    filters = [Budget.user_id == user_id]
    if not include_archived:
        filters.append(Budget.archived_at.is_(None))

    total = await session.scalar(
        select(func.count()).select_from(Budget).where(*filters),
    )
    result = await session.execute(
        select(Budget)
        .options(selectinload(Budget.categories))
        .where(*filters)
        .order_by(Budget.start_date.desc(), Budget.name.asc(), Budget.id.asc())
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)


async def archive_budget(session: AsyncSession, budget: Budget) -> None:
    budget.archived_at = datetime.now(UTC)
    await session.flush()


async def replace_budget_categories(
    session: AsyncSession,
    *,
    budget_id: uuid.UUID,
    category_ids: list[uuid.UUID],
) -> None:
    await session.execute(
        delete(budget_categories).where(budget_categories.c.budget_id == budget_id),
    )
    if category_ids:
        await session.execute(
            insert(budget_categories),
            [
                {"budget_id": budget_id, "category_id": category_id}
                for category_id in category_ids
            ],
        )
    await session.flush()


async def sum_budget_expenses(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    currency: str,
    period_start: date,
    period_end: date,
    category_ids: list[uuid.UUID] | None,
) -> Decimal:
    """Sum expense transactions for budget utilization (transfers excluded)."""
    if category_ids is not None and not category_ids:
        return Decimal("0")

    filters = [
        Transaction.user_id == user_id,
        Transaction.deleted_at.is_(None),
        Transaction.transaction_type == TransactionType.EXPENSE,
        Transaction.currency == currency,
        Transaction.transaction_date >= period_start,
        Transaction.transaction_date <= period_end,
    ]
    if category_ids is not None:
        filters.append(Transaction.category_id.in_(category_ids))

    total = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(*filters),
    )
    return Decimal(total or 0)
