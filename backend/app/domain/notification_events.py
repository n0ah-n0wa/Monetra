"""Domain helpers for application notifications."""

from __future__ import annotations

from decimal import Decimal

from app.domain.transactions import normalize_money

GOAL_MILESTONE_PERCENTS = (25, 50, 75, 100)


def completion_percentage(
    *,
    current_amount: Decimal,
    target_amount: Decimal,
) -> Decimal:
    """Exact completion percentage capped at 100."""
    target = normalize_money(target_amount)
    current = normalize_money(current_amount)
    if target <= Decimal("0"):
        return Decimal("100") if current >= Decimal("0") else Decimal("0")
    if current <= Decimal("0"):
        return Decimal("0")
    raw = (current / target) * Decimal("100")
    if raw >= Decimal("100"):
        return Decimal("100")
    return raw.quantize(Decimal("0.01"))


def crossed_goal_milestones(
    *,
    previous_percentage: Decimal,
    current_percentage: Decimal,
) -> list[int]:
    """Return milestone percents newly reached when progress increases."""
    if current_percentage <= previous_percentage:
        return []
    return [
        milestone
        for milestone in GOAL_MILESTONE_PERCENTS
        if previous_percentage < Decimal(milestone) <= current_percentage
    ]
