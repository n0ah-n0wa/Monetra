"""Analytics calculation domain rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.transactions import normalize_money


@dataclass(frozen=True)
class IncomeExpenseTotals:
    income: Decimal
    expenses: Decimal


def compute_net_cash_flow(*, income: Decimal, expenses: Decimal) -> Decimal:
    return normalize_money(income - expenses)


def compute_savings_rate(*, income: Decimal, expenses: Decimal) -> Decimal | None:
    if income <= Decimal("0"):
        return None
    net = compute_net_cash_flow(income=income, expenses=expenses)
    return normalize_money((net / income) * Decimal("100"))


def compute_period_change(
    *,
    current: Decimal,
    previous: Decimal,
) -> Decimal:
    return normalize_money(current - previous)


def compute_period_change_percent(
    *,
    current: Decimal,
    previous: Decimal,
) -> Decimal | None:
    if previous == Decimal("0"):
        return None
    change = compute_period_change(current=current, previous=previous)
    return normalize_money((change / previous) * Decimal("100"))
