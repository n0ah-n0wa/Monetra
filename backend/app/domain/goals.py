"""Financial goal progress domain rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal

from app.domain.transactions import normalize_money


@dataclass(frozen=True)
class ContributionPoint:
    contribution_date: date
    cumulative_amount: Decimal


@dataclass(frozen=True)
class GoalProgressMetrics:
    remaining_amount: Decimal
    completion_percentage: Decimal
    required_average_contribution: Decimal | None
    average_contribution_rate: Decimal | None
    projected_completion_date: date | None
    target_date_achievable: bool | None


def compute_remaining_amount(
    *, target_amount: Decimal, current_amount: Decimal
) -> Decimal:
    remaining = normalize_money(target_amount - current_amount)
    if remaining < Decimal("0"):
        return Decimal("0.0000")
    return remaining


def compute_completion_percentage(
    *,
    target_amount: Decimal,
    current_amount: Decimal,
) -> Decimal:
    if target_amount <= Decimal("0"):
        return Decimal("0.0000")
    percentage = normalize_money((current_amount / target_amount) * Decimal("100"))
    if percentage > Decimal("100.0000"):
        return Decimal("100.0000")
    if percentage < Decimal("0.0000"):
        return Decimal("0.0000")
    return percentage


def compute_required_average_contribution(
    *,
    remaining_amount: Decimal,
    target_date: date | None,
    as_of_date: date,
) -> Decimal | None:
    if target_date is None:
        return None
    days_remaining = (target_date - as_of_date).days
    if days_remaining <= 0:
        return None
    if remaining_amount <= Decimal("0"):
        return Decimal("0.0000")
    return normalize_money(remaining_amount / Decimal(days_remaining))


def build_cumulative_contribution_history(
    daily_net_contributions: dict[date, Decimal],
) -> list[ContributionPoint]:
    if not daily_net_contributions:
        return []

    cumulative = Decimal("0.0000")
    history: list[ContributionPoint] = []
    for contribution_date in sorted(daily_net_contributions):
        cumulative = normalize_money(
            cumulative + daily_net_contributions[contribution_date],
        )
        history.append(
            ContributionPoint(
                contribution_date=contribution_date,
                cumulative_amount=cumulative,
            ),
        )
    return history


def compute_average_contribution_rate(
    history: list[ContributionPoint],
) -> Decimal | None:
    if len(history) < 2:
        return None

    first = history[0]
    last = history[-1]
    elapsed_days = (last.contribution_date - first.contribution_date).days
    if elapsed_days <= 0:
        return None

    delta = normalize_money(last.cumulative_amount - first.cumulative_amount)
    return normalize_money(delta / Decimal(elapsed_days))


def compute_projected_completion_date(
    *,
    current_amount: Decimal,
    target_amount: Decimal,
    average_contribution_rate: Decimal | None,
    as_of_date: date,
) -> date | None:
    if current_amount >= target_amount:
        return as_of_date
    if average_contribution_rate is None or average_contribution_rate <= Decimal("0"):
        return None

    remaining = normalize_money(target_amount - current_amount)
    days_needed = int(
        (remaining / average_contribution_rate).quantize(
            Decimal("1"),
            rounding=ROUND_CEILING,
        ),
    )
    if days_needed <= 0:
        return as_of_date
    return as_of_date + timedelta(days=days_needed)


def is_target_date_achievable(
    *,
    target_date: date | None,
    projected_completion_date: date | None,
) -> bool | None:
    if target_date is None:
        return None
    if projected_completion_date is None:
        return False
    return projected_completion_date <= target_date


def compute_goal_progress(
    *,
    target_amount: Decimal,
    current_amount: Decimal,
    target_date: date | None,
    as_of_date: date,
    contribution_history: list[ContributionPoint],
) -> GoalProgressMetrics:
    remaining = compute_remaining_amount(
        target_amount=target_amount,
        current_amount=current_amount,
    )
    completion = compute_completion_percentage(
        target_amount=target_amount,
        current_amount=current_amount,
    )
    required_average = compute_required_average_contribution(
        remaining_amount=remaining,
        target_date=target_date,
        as_of_date=as_of_date,
    )

    average_rate = compute_average_contribution_rate(contribution_history)
    projected = compute_projected_completion_date(
        current_amount=current_amount,
        target_amount=target_amount,
        average_contribution_rate=average_rate,
        as_of_date=as_of_date,
    )
    achievable = is_target_date_achievable(
        target_date=target_date,
        projected_completion_date=projected,
    )

    return GoalProgressMetrics(
        remaining_amount=remaining,
        completion_percentage=completion,
        required_average_contribution=required_average,
        average_contribution_rate=average_rate,
        projected_completion_date=projected,
        target_date_achievable=achievable,
    )
