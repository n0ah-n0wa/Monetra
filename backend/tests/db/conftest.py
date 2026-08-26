"""Database integration test fixtures."""

from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal

import pytest
from app.db.session import create_async_engine_from_settings, ping_database
from app.models.category import Category
from app.models.enums import (
    AccountType,
    CategoryType,
    TransactionType,
)
from app.models.financial_account import FinancialAccount
from app.models.transaction import Transaction
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@pytest.fixture
async def db_engine(app_settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine_from_settings(app_settings)
    if not await ping_database(engine):
        await engine.dispose()
        pytest.skip("PostgreSQL is not available")
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield a session wrapped in a connection transaction that always rolls back."""
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    entity = User(email="user@example.com", password_hash="hashed-password")
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    entity = User(email="other@example.com", password_hash="hashed-password")
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def account(db_session: AsyncSession, user: User) -> FinancialAccount:
    entity = FinancialAccount(
        user_id=user.id,
        name="Checking",
        account_type=AccountType.BANK,
        currency="USD",
        opening_balance=Decimal("1000.0000"),
        current_balance=Decimal("1000.0000"),
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def other_account(db_session: AsyncSession, user: User) -> FinancialAccount:
    entity = FinancialAccount(
        user_id=user.id,
        name="Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
        opening_balance=Decimal("500.0000"),
        current_balance=Decimal("500.0000"),
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def expense_category(db_session: AsyncSession, user: User) -> Category:
    entity = Category(
        user_id=user.id,
        name="Groceries",
        category_type=CategoryType.EXPENSE,
        is_system=False,
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def system_category(db_session: AsyncSession) -> Category:
    entity = Category(
        user_id=None,
        name="Uncategorized",
        category_type=CategoryType.UNIVERSAL,
        is_system=True,
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


def make_transaction(
    *,
    user: User,
    account: FinancialAccount,
    category: Category,
    amount: Decimal = Decimal("42.5000"),
) -> Transaction:
    return Transaction(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id,
        transaction_type=TransactionType.EXPENSE,
        amount=amount,
        currency=account.currency,
        description="Test purchase",
        transaction_date=date(2026, 1, 15),
    )
