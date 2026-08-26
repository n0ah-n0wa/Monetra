"""User-scoped resource access helpers.

All lookups are constrained to the authenticated user's ownership boundary.
Cross-user identifiers return ``NotFoundError`` to avoid resource enumeration.
"""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.budget import Budget
from app.models.category import Category
from app.models.financial_account import FinancialAccount
from app.models.financial_goal import FinancialGoal
from app.models.transaction import Transaction


async def get_owned_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> FinancialAccount:
    result = await session.execute(
        select(FinancialAccount).where(
            FinancialAccount.id == account_id,
            FinancialAccount.user_id == user_id,
        ),
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise NotFoundError(
            code="ACCOUNT_NOT_FOUND",
            message="Financial account was not found.",
        )
    return account


async def get_owned_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> Transaction:
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        ),
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise NotFoundError(
            code="TRANSACTION_NOT_FOUND",
            message="Transaction was not found.",
        )
    return transaction


async def get_owned_budget(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> Budget:
    result = await session.execute(
        select(Budget).where(
            Budget.id == budget_id,
            Budget.user_id == user_id,
        ),
    )
    budget = result.scalar_one_or_none()
    if budget is None:
        raise NotFoundError(
            code="BUDGET_NOT_FOUND",
            message="Budget was not found.",
        )
    return budget


async def get_owned_goal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
) -> FinancialGoal:
    result = await session.execute(
        select(FinancialGoal).where(
            FinancialGoal.id == goal_id,
            FinancialGoal.user_id == user_id,
        ),
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise NotFoundError(
            code="GOAL_NOT_FOUND",
            message="Financial goal was not found.",
        )
    return goal


async def get_accessible_category(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category:
    """Return a user-owned or system category; reject other users' categories."""
    result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            or_(Category.user_id.is_(None), Category.user_id == user_id),
        ),
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise NotFoundError(
            code="CATEGORY_NOT_FOUND",
            message="Category was not found.",
        )
    return category


async def get_owned_user_category(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category:
    """Return a category owned by the user (excludes system categories)."""
    result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        ),
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise NotFoundError(
            code="CATEGORY_NOT_FOUND",
            message="Category was not found.",
        )
    return category
