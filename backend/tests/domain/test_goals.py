"""Financial goal domain tests."""

from datetime import date
from decimal import Decimal

from app.domain.goals import (
    ContributionPoint,
    build_cumulative_contribution_history,
    compute_average_contribution_rate,
    compute_completion_percentage,
    compute_goal_progress,
    compute_projected_completion_date,
    compute_remaining_amount,
    compute_required_average_contribution,
    is_target_date_achievable,
)


def test_compute_remaining_amount_never_negative() -> None:
    assert compute_remaining_amount(
        target_amount=Decimal("100.0000"),
        current_amount=Decimal("150.0000"),
    ) == Decimal("0.0000")


def test_compute_completion_percentage_caps_at_one_hundred() -> None:
    assert compute_completion_percentage(
        target_amount=Decimal("100.0000"),
        current_amount=Decimal("250.0000"),
    ) == Decimal("100.0000")


def test_compute_completion_percentage_decimal_precision() -> None:
    result = compute_completion_percentage(
        target_amount=Decimal("300.0000"),
        current_amount=Decimal("100.0000"),
    )
    assert result == Decimal("33.3333")


def test_compute_required_average_contribution_for_future_target_date() -> None:
    result = compute_required_average_contribution(
        remaining_amount=Decimal("900.0000"),
        target_date=date(2026, 1, 31),
        as_of_date=date(2026, 1, 1),
    )
    assert result == Decimal("30.0000")


def test_compute_required_average_contribution_returns_none_for_past_target() -> None:
    assert (
        compute_required_average_contribution(
            remaining_amount=Decimal("100.0000"),
            target_date=date(2025, 12, 31),
            as_of_date=date(2026, 1, 15),
        )
        is None
    )


def test_compute_average_contribution_rate_handles_zero_delta() -> None:
    history = [
        ContributionPoint(date(2026, 1, 1), Decimal("100.0000")),
        ContributionPoint(date(2026, 1, 11), Decimal("100.0000")),
    ]
    assert compute_average_contribution_rate(history) == Decimal("0.0000")


def test_compute_average_contribution_rate_returns_none_with_insufficient_history() -> (
    None
):
    history = [ContributionPoint(date(2026, 1, 1), Decimal("50.0000"))]
    assert compute_average_contribution_rate(history) is None


def test_compute_projected_completion_date_with_zero_rate_returns_none() -> None:
    assert (
        compute_projected_completion_date(
            current_amount=Decimal("100.0000"),
            target_amount=Decimal("1000.0000"),
            average_contribution_rate=Decimal("0.0000"),
            as_of_date=date(2026, 1, 1),
        )
        is None
    )


def test_compute_projected_completion_date_when_target_already_reached() -> None:
    assert compute_projected_completion_date(
        current_amount=Decimal("1000.0000"),
        target_amount=Decimal("1000.0000"),
        average_contribution_rate=Decimal("10.0000"),
        as_of_date=date(2026, 1, 15),
    ) == date(2026, 1, 15)


def test_build_cumulative_contribution_history() -> None:
    history = build_cumulative_contribution_history(
        {
            date(2026, 1, 1): Decimal("10.0000"),
            date(2026, 1, 2): Decimal("5.0000"),
        },
    )
    assert history[0].cumulative_amount == Decimal("10.0000")
    assert history[1].cumulative_amount == Decimal("15.0000")


def test_compute_goal_progress_with_missing_history() -> None:
    metrics = compute_goal_progress(
        target_amount=Decimal("1000.0000"),
        current_amount=Decimal("200.0000"),
        target_date=date(2026, 6, 1),
        as_of_date=date(2026, 1, 1),
        contribution_history=[],
    )
    assert metrics.remaining_amount == Decimal("800.0000")
    assert metrics.average_contribution_rate is None
    assert metrics.projected_completion_date is None
    assert metrics.target_date_achievable is False


def test_compute_goal_progress_positive_rate_projection() -> None:
    metrics = compute_goal_progress(
        target_amount=Decimal("1000.0000"),
        current_amount=Decimal("100.0000"),
        target_date=date(2026, 4, 1),
        as_of_date=date(2026, 1, 1),
        contribution_history=[
            ContributionPoint(date(2026, 1, 1), Decimal("0.0000")),
            ContributionPoint(date(2026, 1, 11), Decimal("100.0000")),
        ],
    )
    assert metrics.average_contribution_rate == Decimal("10.0000")
    assert metrics.projected_completion_date == date(2026, 4, 1)
    assert metrics.target_date_achievable is True


def test_is_target_date_achievable_without_target_date() -> None:
    assert (
        is_target_date_achievable(
            target_date=None,
            projected_completion_date=date(2026, 5, 1),
        )
        is None
    )
