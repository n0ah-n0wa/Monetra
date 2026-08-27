"""Budget period and utilization domain rules."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.core.exceptions import ValidationAppError
from app.domain.transactions import normalize_money
from app.models.enums import BudgetPeriod, BudgetStatus


def validate_budget_date_range(*, start_date: date, end_date: date | None) -> None:
    if end_date is not None and end_date < start_date:
        raise ValidationAppError(
            code="INVALID_DATE_RANGE",
            message="end_date must be on or after start_date.",
        )


def _anchor_day(start_date: date) -> int:
    return start_date.day


def _add_months(source: date, months: int, *, anchor_day: int) -> date:
    month_index = source.month - 1 + months
    year = source.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(anchor_day, last_day))


def _clamp_window_end(
    window_end: date,
    *,
    budget_end: date | None,
) -> date:
    if budget_end is not None:
        return min(window_end, budget_end)
    return window_end


def resolve_period_window(
    *,
    period: BudgetPeriod,
    budget_start: date,
    budget_end: date | None,
    as_of: date,
) -> tuple[date, date] | None:
    """Return the measurement window containing ``as_of``, if the budget is active."""
    if as_of < budget_start:
        return None
    if budget_end is not None and as_of > budget_end:
        return None

    if period == BudgetPeriod.CUSTOM:
        if budget_end is None:
            raise ValidationAppError(
                code="INVALID_BUDGET_PERIOD",
                message="Custom budgets require an end_date.",
            )
        return budget_start, budget_end

    if period == BudgetPeriod.WEEKLY:
        days_since_start = (as_of - budget_start).days
        period_index = days_since_start // 7
        window_start = budget_start + timedelta(days=period_index * 7)
        window_end = window_start + timedelta(days=6)
        return window_start, _clamp_window_end(window_end, budget_end=budget_end)

    if period == BudgetPeriod.MONTHLY:
        window_start = budget_start
        anchor_day = _anchor_day(budget_start)
        while True:
            next_start = _add_months(window_start, 1, anchor_day=anchor_day)
            if as_of < next_start:
                window_end = next_start - timedelta(days=1)
                return window_start, _clamp_window_end(
                    window_end,
                    budget_end=budget_end,
                )
            window_start = next_start

    if period == BudgetPeriod.YEARLY:
        window_start = budget_start
        anchor_day = _anchor_day(budget_start)
        while True:
            next_start = _add_months(window_start, 12, anchor_day=anchor_day)
            if as_of < next_start:
                window_end = next_start - timedelta(days=1)
                return window_start, _clamp_window_end(
                    window_end,
                    budget_end=budget_end,
                )
            window_start = next_start

    raise ValidationAppError(
        code="INVALID_BUDGET_PERIOD",
        message="Unsupported budget period.",
    )


def compute_percentage_used(*, spent: Decimal, amount: Decimal) -> Decimal:
    if amount <= Decimal("0"):
        return Decimal("0.0000")
    return normalize_money((spent / amount) * Decimal("100"))


def compute_budget_status(
    *,
    spent: Decimal,
    amount: Decimal,
    warning_threshold_percent: int,
) -> BudgetStatus:
    if spent > amount:
        return BudgetStatus.EXCEEDED
    warning_amount = normalize_money(
        amount * Decimal(warning_threshold_percent) / Decimal("100"),
    )
    if spent >= warning_amount:
        return BudgetStatus.WARNING
    return BudgetStatus.HEALTHY


@dataclass(frozen=True)
class BudgetUtilization:
    period_start: date
    period_end: date
    budget_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: Decimal
    status: BudgetStatus


def compute_budget_utilization(
    *,
    period_start: date,
    period_end: date,
    budget_amount: Decimal,
    spent_amount: Decimal,
    warning_threshold_percent: int,
) -> BudgetUtilization:
    normalized_spent = normalize_money(spent_amount)
    normalized_budget = normalize_money(budget_amount)
    remaining = normalize_money(normalized_budget - normalized_spent)
    percentage = compute_percentage_used(
        spent=normalized_spent,
        amount=normalized_budget,
    )
    status = compute_budget_status(
        spent=normalized_spent,
        amount=normalized_budget,
        warning_threshold_percent=warning_threshold_percent,
    )
    return BudgetUtilization(
        period_start=period_start,
        period_end=period_end,
        budget_amount=normalized_budget,
        spent_amount=normalized_spent,
        remaining_amount=remaining,
        percentage_used=percentage,
        status=status,
    )
