"""Domain tests for notification milestone helpers."""

from decimal import Decimal

from app.domain.notification_events import (
    completion_percentage,
    crossed_goal_milestones,
)


def test_completion_percentage_and_milestones() -> None:
    assert completion_percentage(
        current_amount=Decimal("25"),
        target_amount=Decimal("100"),
    ) == Decimal("25.00")
    assert crossed_goal_milestones(
        previous_percentage=Decimal("0"),
        current_percentage=Decimal("50"),
    ) == [25, 50]
    assert (
        crossed_goal_milestones(
            previous_percentage=Decimal("50"),
            current_percentage=Decimal("50"),
        )
        == []
    )
    assert crossed_goal_milestones(
        previous_percentage=Decimal("90"),
        current_percentage=Decimal("100"),
    ) == [100]
