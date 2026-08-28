"""Budget utilization caching tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.models.budget import Budget
from app.models.enums import BudgetPeriod, BudgetScope
from app.services import budget_service


@pytest.mark.asyncio
async def test_compute_utilization_reuses_spent_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget = Budget(
        id=uuid4(),
        user_id=uuid4(),
        name="Food",
        period=BudgetPeriod.MONTHLY,
        scope=BudgetScope.OVERALL,
        amount=Decimal("500.0000"),
        currency="USD",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        warning_threshold_percent=80,
    )
    budget.categories = []
    sum_expenses = AsyncMock(return_value=Decimal("100.0000"))
    monkeypatch.setattr(budget_service.budget_repo, "sum_budget_expenses", sum_expenses)

    session = MagicMock()
    spent_cache: dict = {}
    as_of = date(2026, 3, 15)

    first = await budget_service._compute_utilization(
        session,
        budget=budget,
        as_of_date=as_of,
        spent_cache=spent_cache,
    )
    second = await budget_service._compute_utilization(
        session,
        budget=budget,
        as_of_date=as_of,
        spent_cache=spent_cache,
    )

    assert first is not None
    assert second is not None
    assert first.spent_amount == second.spent_amount == Decimal("100.0000")
    sum_expenses.assert_awaited_once()
