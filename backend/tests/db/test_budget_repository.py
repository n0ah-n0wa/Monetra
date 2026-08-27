"""Budget repository regression tests."""

from datetime import date
from decimal import Decimal

import pytest
from app.repositories import budget_repository as budget_repo
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_sum_budget_expenses_returns_zero_for_empty_category_list(
    db_session: AsyncSession,
    user,
) -> None:
    total = await budget_repo.sum_budget_expenses(
        db_session,
        user_id=user.id,
        currency="USD",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        category_ids=[],
    )
    assert total == Decimal("0")
