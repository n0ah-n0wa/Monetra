"""Budget domain tests."""

from datetime import date
from decimal import Decimal

import pytest
from app.core.exceptions import ValidationAppError
from app.domain.budgets import (
    compute_budget_status,
    compute_budget_utilization,
    compute_percentage_used,
    resolve_period_window,
)
from app.models.enums import BudgetPeriod, BudgetStatus


def test_resolve_weekly_period_window() -> None:
    window = resolve_period_window(
        period=BudgetPeriod.WEEKLY,
        budget_start=date(2026, 1, 1),
        budget_end=None,
        as_of=date(2026, 1, 10),
    )
    assert window == (date(2026, 1, 8), date(2026, 1, 14))


def test_resolve_monthly_period_handles_month_end() -> None:
    window = resolve_period_window(
        period=BudgetPeriod.MONTHLY,
        budget_start=date(2026, 1, 31),
        budget_end=None,
        as_of=date(2026, 2, 15),
    )
    assert window == (date(2026, 1, 31), date(2026, 2, 27))


def test_resolve_yearly_period_leap_day_anchor() -> None:
    window = resolve_period_window(
        period=BudgetPeriod.YEARLY,
        budget_start=date(2024, 2, 29),
        budget_end=None,
        as_of=date(2025, 3, 1),
    )
    assert window == (date(2025, 2, 28), date(2026, 2, 27))


def test_resolve_custom_period_requires_end_date() -> None:
    with pytest.raises(ValidationAppError) as exc:
        resolve_period_window(
            period=BudgetPeriod.CUSTOM,
            budget_start=date(2026, 1, 1),
            budget_end=None,
            as_of=date(2026, 1, 15),
        )
    assert exc.value.code == "INVALID_BUDGET_PERIOD"


def test_resolve_period_returns_none_before_budget_start() -> None:
    assert (
        resolve_period_window(
            period=BudgetPeriod.MONTHLY,
            budget_start=date(2026, 2, 1),
            budget_end=None,
            as_of=date(2026, 1, 31),
        )
        is None
    )


def test_compute_budget_utilization_decimal_precision() -> None:
    result = compute_budget_utilization(
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        budget_amount=Decimal("100.0000"),
        spent_amount=Decimal("33.3333"),
        warning_threshold_percent=80,
    )
    assert result.spent_amount == Decimal("33.3333")
    assert result.remaining_amount == Decimal("66.6667")
    assert result.percentage_used == Decimal("33.3333")
    assert result.status is BudgetStatus.HEALTHY


@pytest.mark.parametrize(
    ("spent", "amount", "threshold", "expected"),
    [
        (Decimal("50.0000"), Decimal("100.0000"), 80, BudgetStatus.HEALTHY),
        (Decimal("80.0000"), Decimal("100.0000"), 80, BudgetStatus.WARNING),
        (Decimal("100.0000"), Decimal("100.0000"), 80, BudgetStatus.WARNING),
        (Decimal("100.0001"), Decimal("100.0000"), 80, BudgetStatus.EXCEEDED),
    ],
)
def test_compute_budget_status_thresholds(
    spent: Decimal,
    amount: Decimal,
    threshold: int,
    expected: BudgetStatus,
) -> None:
    assert (
        compute_budget_status(
            spent=spent,
            amount=amount,
            warning_threshold_percent=threshold,
        )
        is expected
    )


def test_compute_percentage_used_can_exceed_one_hundred() -> None:
    assert compute_percentage_used(
        spent=Decimal("150.0000"),
        amount=Decimal("100.0000"),
    ) == Decimal("150.0000")
