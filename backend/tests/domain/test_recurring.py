"""Recurring schedule domain tests."""

from datetime import date

import pytest
from app.domain.recurring import (
    advance_execution_date,
    advance_next_execution_pointer,
    due_execution_dates,
    initial_next_execution_date,
    recompute_next_execution_date,
)
from app.models.enums import RecurringFrequency


@pytest.mark.parametrize(
    ("frequency", "current", "start", "expected"),
    [
        (
            RecurringFrequency.DAILY,
            date(2026, 1, 1),
            date(2026, 1, 1),
            date(2026, 1, 2),
        ),
        (
            RecurringFrequency.WEEKLY,
            date(2026, 1, 1),
            date(2026, 1, 1),
            date(2026, 1, 8),
        ),
        (
            RecurringFrequency.BIWEEKLY,
            date(2026, 1, 1),
            date(2026, 1, 1),
            date(2026, 1, 15),
        ),
        (
            RecurringFrequency.MONTHLY,
            date(2026, 1, 31),
            date(2026, 1, 31),
            date(2026, 2, 28),
        ),
        (
            RecurringFrequency.MONTHLY,
            date(2026, 2, 28),
            date(2026, 1, 31),
            date(2026, 3, 31),
        ),
        (
            RecurringFrequency.QUARTERLY,
            date(2026, 1, 15),
            date(2026, 1, 15),
            date(2026, 4, 15),
        ),
        (
            RecurringFrequency.YEARLY,
            date(2024, 2, 29),
            date(2024, 2, 29),
            date(2025, 2, 28),
        ),
        (
            RecurringFrequency.YEARLY,
            date(2025, 2, 28),
            date(2024, 2, 29),
            date(2026, 2, 28),
        ),
    ],
)
def test_advance_execution_date(
    frequency: RecurringFrequency,
    current: date,
    start: date,
    expected: date,
) -> None:
    result = advance_execution_date(current, frequency, start_date=start)
    assert result == expected


def test_initial_next_execution_date_is_start_date() -> None:
    assert initial_next_execution_date(date(2026, 3, 15)) == date(2026, 3, 15)


def test_due_execution_dates_collects_missed_daily_runs() -> None:
    due = due_execution_dates(
        next_execution_date=date(2026, 1, 1),
        frequency=RecurringFrequency.DAILY,
        start_date=date(2026, 1, 1),
        end_date=None,
        as_of_date=date(2026, 1, 3),
        executed_dates=set(),
    )
    assert due == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]


def test_due_execution_dates_skips_already_executed_dates() -> None:
    due = due_execution_dates(
        next_execution_date=date(2026, 1, 1),
        frequency=RecurringFrequency.DAILY,
        start_date=date(2026, 1, 1),
        end_date=None,
        as_of_date=date(2026, 1, 3),
        executed_dates={date(2026, 1, 2)},
    )
    assert due == [date(2026, 1, 1), date(2026, 1, 3)]


def test_due_execution_dates_respects_end_date() -> None:
    due = due_execution_dates(
        next_execution_date=date(2026, 1, 1),
        frequency=RecurringFrequency.DAILY,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        as_of_date=date(2026, 1, 5),
        executed_dates=set(),
    )
    assert due == [date(2026, 1, 1), date(2026, 1, 2)]


def test_recompute_next_execution_date_skips_executed_and_leap_year_anchor() -> None:
    result = recompute_next_execution_date(
        start_date=date(2024, 2, 29),
        frequency=RecurringFrequency.YEARLY,
        end_date=None,
        as_of_date=date(2026, 3, 1),
        executed_dates={date(2026, 2, 28)},
    )
    assert result == date(2027, 2, 28)


def test_recompute_next_execution_date_returns_none_after_end_date() -> None:
    result = recompute_next_execution_date(
        start_date=date(2026, 1, 1),
        frequency=RecurringFrequency.MONTHLY,
        end_date=date(2026, 2, 1),
        as_of_date=date(2026, 3, 1),
        executed_dates=set(),
    )
    assert result is None


def test_advance_next_execution_pointer_skips_executed_same_day() -> None:
    result = advance_next_execution_pointer(
        next_execution_date=date(2026, 1, 1),
        frequency=RecurringFrequency.WEEKLY,
        start_date=date(2026, 1, 1),
        end_date=None,
        as_of_date=date(2026, 1, 1),
        executed_dates={date(2026, 1, 1)},
    )
    assert result == date(2026, 1, 8)


def test_advance_next_execution_pointer_returns_none_past_end_date() -> None:
    result = advance_next_execution_pointer(
        next_execution_date=date(2026, 1, 1),
        frequency=RecurringFrequency.DAILY,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        as_of_date=date(2026, 1, 1),
        executed_dates={date(2026, 1, 1)},
    )
    assert result is None
