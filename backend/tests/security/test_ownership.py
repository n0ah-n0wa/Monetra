"""Horizontal privilege escalation tests for ownership-scoped resource access."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.core.exceptions import NotFoundError
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import (
    AccountType,
    BudgetPeriod,
    BudgetScope,
    CategoryType,
    GoalStatus,
)
from app.models.financial_account import FinancialAccount
from app.models.financial_goal import FinancialGoal
from app.models.transaction import Transaction
from app.models.user import User
from app.services import ownership
from sqlalchemy.ext.asyncio import AsyncSession

from tests.db.conftest import make_transaction


@pytest.fixture
async def user_account(db_session: AsyncSession, user: User) -> FinancialAccount:
    entity = FinancialAccount(
        user_id=user.id,
        name="User Checking",
        account_type=AccountType.BANK,
        currency="USD",
        opening_balance=Decimal("100.0000"),
        current_balance=Decimal("100.0000"),
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def other_account(db_session: AsyncSession, other_user: User) -> FinancialAccount:
    entity = FinancialAccount(
        user_id=other_user.id,
        name="Other Checking",
        account_type=AccountType.BANK,
        currency="USD",
        opening_balance=Decimal("50.0000"),
        current_balance=Decimal("50.0000"),
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def user_category(db_session: AsyncSession, user: User) -> Category:
    entity = Category(
        user_id=user.id,
        name="User Groceries",
        category_type=CategoryType.EXPENSE,
        is_system=False,
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def other_category(db_session: AsyncSession, other_user: User) -> Category:
    entity = Category(
        user_id=other_user.id,
        name="Other Groceries",
        category_type=CategoryType.EXPENSE,
        is_system=False,
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def user_transaction(
    db_session: AsyncSession,
    user: User,
    user_account: FinancialAccount,
    user_category: Category,
) -> Transaction:
    entity = make_transaction(user=user, account=user_account, category=user_category)
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def other_transaction(
    db_session: AsyncSession,
    other_user: User,
    other_account: FinancialAccount,
    other_category: Category,
) -> Transaction:
    entity = make_transaction(
        user=other_user,
        account=other_account,
        category=other_category,
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def user_budget(db_session: AsyncSession, user: User) -> Budget:
    entity = Budget(
        user_id=user.id,
        name="User Budget",
        period=BudgetPeriod.MONTHLY,
        scope=BudgetScope.OVERALL,
        amount=Decimal("500.0000"),
        currency="USD",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def other_budget(db_session: AsyncSession, other_user: User) -> Budget:
    entity = Budget(
        user_id=other_user.id,
        name="Other Budget",
        period=BudgetPeriod.MONTHLY,
        scope=BudgetScope.OVERALL,
        amount=Decimal("300.0000"),
        currency="USD",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def user_goal(db_session: AsyncSession, user: User) -> FinancialGoal:
    entity = FinancialGoal(
        user_id=user.id,
        name="User Goal",
        target_amount=Decimal("1000.0000"),
        current_amount=Decimal("100.0000"),
        currency="USD",
        status=GoalStatus.ACTIVE,
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def other_goal(db_session: AsyncSession, other_user: User) -> FinancialGoal:
    entity = FinancialGoal(
        user_id=other_user.id,
        name="Other Goal",
        target_amount=Decimal("2000.0000"),
        current_amount=Decimal("200.0000"),
        currency="USD",
        status=GoalStatus.ACTIVE,
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


async def test_user_cannot_access_other_users_account(
    db_session: AsyncSession,
    user: User,
    other_account: FinancialAccount,
) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        await ownership.get_owned_account(
            db_session,
            user_id=user.id,
            account_id=other_account.id,
        )
    assert exc_info.value.code == "ACCOUNT_NOT_FOUND"


async def test_user_cannot_access_other_users_transaction(
    db_session: AsyncSession,
    user: User,
    other_transaction: Transaction,
) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        await ownership.get_owned_transaction(
            db_session,
            user_id=user.id,
            transaction_id=other_transaction.id,
        )
    assert exc_info.value.code == "TRANSACTION_NOT_FOUND"


async def test_user_cannot_access_other_users_budget(
    db_session: AsyncSession,
    user: User,
    other_budget: Budget,
) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        await ownership.get_owned_budget(
            db_session,
            user_id=user.id,
            budget_id=other_budget.id,
        )
    assert exc_info.value.code == "BUDGET_NOT_FOUND"


async def test_user_cannot_access_other_users_goal(
    db_session: AsyncSession,
    user: User,
    other_goal: FinancialGoal,
) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        await ownership.get_owned_goal(
            db_session,
            user_id=user.id,
            goal_id=other_goal.id,
        )
    assert exc_info.value.code == "GOAL_NOT_FOUND"


async def test_user_cannot_access_other_users_category(
    db_session: AsyncSession,
    user: User,
    other_category: Category,
) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        await ownership.get_owned_user_category(
            db_session,
            user_id=user.id,
            category_id=other_category.id,
        )
    assert exc_info.value.code == "CATEGORY_NOT_FOUND"


async def test_user_can_access_own_resources(
    db_session: AsyncSession,
    user: User,
    user_account: FinancialAccount,
    user_transaction: Transaction,
    user_budget: Budget,
    user_goal: FinancialGoal,
    user_category: Category,
) -> None:
    assert (
        await ownership.get_owned_account(
            db_session,
            user_id=user.id,
            account_id=user_account.id,
        )
    ).id == user_account.id
    assert (
        await ownership.get_owned_transaction(
            db_session,
            user_id=user.id,
            transaction_id=user_transaction.id,
        )
    ).id == user_transaction.id
    assert (
        await ownership.get_owned_budget(
            db_session,
            user_id=user.id,
            budget_id=user_budget.id,
        )
    ).id == user_budget.id
    assert (
        await ownership.get_owned_goal(
            db_session,
            user_id=user.id,
            goal_id=user_goal.id,
        )
    ).id == user_goal.id
    assert (
        await ownership.get_owned_user_category(
            db_session,
            user_id=user.id,
            category_id=user_category.id,
        )
    ).id == user_category.id


async def test_user_can_read_system_category(
    db_session: AsyncSession,
    user: User,
    system_category: Category,
) -> None:
    category = await ownership.get_accessible_category(
        db_session,
        user_id=user.id,
        category_id=system_category.id,
    )
    assert category.is_system is True
    assert category.user_id is None
