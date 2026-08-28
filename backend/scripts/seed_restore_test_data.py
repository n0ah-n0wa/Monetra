"""Seed representative financial data for backup/restore drills.

Runs inside the production backend image (no loadtest dependency).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date
from decimal import Decimal

from app.core.config import get_settings
from app.core.exceptions import ConflictError
from app.db.session import dispose_db, get_session_factory, init_db
from app.models.category import Category
from app.models.enums import CategoryType, TransactionType
from app.schemas.accounts import AccountCreateRequest
from app.schemas.transactions import TransactionCreateRequest
from app.schemas.transfers import TransferCreateRequest
from app.services import (
    account_service,
    auth_service,
    transaction_service,
    transfer_service,
)
from app.services.balance_service import assert_user_balance_invariant
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SEED_EMAIL = "restore-test@example.com"
SEED_PASSWORD = "RestoreTest1!"  # noqa: S105 - non-production drill credential only


async def _category_id(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    category_type: CategoryType,
) -> uuid.UUID:
    result = await session.execute(
        select(Category).where(
            Category.user_id == user_id,
            Category.name == name,
            Category.category_type == category_type,
        ),
    )
    category = result.scalar_one_or_none()
    if category is None:
        msg = f"category {name!r} not found for user"
        raise RuntimeError(msg)
    return category.id


async def _run() -> int:
    settings = get_settings()
    init_db(settings)
    factory = get_session_factory()

    async with factory() as session:
        try:
            user, _tokens = await auth_service.register_user(
                session,
                email=SEED_EMAIL,
                password=SEED_PASSWORD,
                settings=settings,
            )
        except ConflictError:
            await session.rollback()
            from app.repositories import user_repository as user_repo

            existing = await user_repo.get_user_by_email(session, SEED_EMAIL)
            if existing is None:
                raise
            user = existing

        checking = await account_service.create_account(
            session,
            user_id=user.id,
            payload=AccountCreateRequest(
                name="Restore Test Checking",
                account_type="bank",
                currency="USD",
                opening_balance=Decimal("2000.0000"),
            ),
        )
        savings = await account_service.create_account(
            session,
            user_id=user.id,
            payload=AccountCreateRequest(
                name="Restore Test Savings",
                account_type="bank",
                currency="USD",
                opening_balance=Decimal("500.0000"),
            ),
        )

        income_category = await _category_id(
            session,
            user_id=user.id,
            name="Salary",
            category_type=CategoryType.INCOME,
        )
        expense_category = await _category_id(
            session,
            user_id=user.id,
            name="Groceries",
            category_type=CategoryType.EXPENSE,
        )

        await transaction_service.create_transaction(
            session,
            user_id=user.id,
            payload=TransactionCreateRequest(
                account_id=checking.id,
                category_id=income_category,
                transaction_type=TransactionType.INCOME,
                amount=Decimal("1500.2500"),
                description="Restore drill paycheck",
                transaction_date=date(2026, 1, 15),
            ),
        )
        await transaction_service.create_transaction(
            session,
            user_id=user.id,
            payload=TransactionCreateRequest(
                account_id=checking.id,
                category_id=expense_category,
                transaction_type=TransactionType.EXPENSE,
                amount=Decimal("123.4567"),
                description="Restore drill groceries",
                transaction_date=date(2026, 1, 31),
            ),
        )
        await transfer_service.create_transfer(
            session,
            user_id=user.id,
            payload=TransferCreateRequest(
                source_account_id=checking.id,
                destination_account_id=savings.id,
                source_amount=Decimal("250.0000"),
                transaction_date=date(2026, 2, 1),
                description="Restore drill savings",
            ),
        )

        await assert_user_balance_invariant(session, user_id=user.id)

    await dispose_db()
    print(
        "restore-test seed complete: "
        f"user={SEED_EMAIL} accounts=2 transactions=2 transfers=1",
    )
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
