"""Recurring transaction schedule domain rules."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from app.core.exceptions import ValidationAppError
from app.models.enums import RecurringFrequency


def validate_date_range(*, start_date: date, end_date: date | None) -> None:
    if end_date is not None and end_date < start_date:
        raise ValidationAppError(
            code="INVALID_DATE_RANGE",
            message="end_date must be on or after start_date.",
        )


def initial_next_execution_date(start_date: date) -> date:
    """Return the first scheduled execution date for a new recurring definition."""
    return start_date


def _anchor_day(start_date: date) -> int:
    return start_date.day


def _add_months(source: date, months: int, *, anchor_day: int) -> date:
    month_index = source.month - 1 + months
    year = source.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(anchor_day, last_day))


def advance_execution_date(
    current: date,
    frequency: RecurringFrequency,
    *,
    start_date: date,
) -> date:
    """Return the schedule date immediately after ``current``."""
    anchor_day = _anchor_day(start_date)
    if frequency == RecurringFrequency.DAILY:
        return current + timedelta(days=1)
    if frequency == RecurringFrequency.WEEKLY:
        return current + timedelta(days=7)
    if frequency == RecurringFrequency.BIWEEKLY:
        return current + timedelta(days=14)
    if frequency == RecurringFrequency.MONTHLY:
        return _add_months(current, 1, anchor_day=anchor_day)
    if frequency == RecurringFrequency.QUARTERLY:
        return _add_months(current, 3, anchor_day=anchor_day)
    if frequency == RecurringFrequency.YEARLY:
        return _add_months(current, 12, anchor_day=anchor_day)
    raise ValidationAppError(
        code="INVALID_FREQUENCY",
        message="Unsupported recurring frequency.",
    )


def is_execution_due(
    execution_date: date,
    *,
    end_date: date | None,
) -> bool:
    return end_date is None or execution_date <= end_date


def due_execution_dates(
    *,
    next_execution_date: date,
    frequency: RecurringFrequency,
    start_date: date,
    end_date: date | None,
    as_of_date: date,
    executed_dates: set[date],
) -> list[date]:
    """Return ordered due dates up to ``as_of_date`` that are not yet executed."""
    due: list[date] = []
    candidate = next_execution_date
    while candidate <= as_of_date:
        if not is_execution_due(candidate, end_date=end_date):
            break
        if candidate not in executed_dates:
            due.append(candidate)
        candidate = advance_execution_date(
            candidate,
            frequency,
            start_date=start_date,
        )
    return due


def advance_next_execution_pointer(
    *,
    next_execution_date: date,
    frequency: RecurringFrequency,
    start_date: date,
    end_date: date | None,
    as_of_date: date,
    executed_dates: set[date],
) -> date | None:
    """Move the schedule pointer past executed dates due on or before ``as_of_date``."""
    candidate = next_execution_date
    while candidate <= as_of_date:
        if not is_execution_due(candidate, end_date=end_date):
            return None
        if candidate not in executed_dates:
            return candidate
        candidate = advance_execution_date(
            candidate,
            frequency,
            start_date=start_date,
        )
    if not is_execution_due(candidate, end_date=end_date):
        return None
    return candidate


def recompute_next_execution_date(
    *,
    start_date: date,
    frequency: RecurringFrequency,
    end_date: date | None,
    as_of_date: date,
    executed_dates: set[date],
) -> date | None:
    """Find the next unexecuted schedule date on or after ``as_of_date``."""
    candidate = start_date
    while candidate < as_of_date:
        candidate = advance_execution_date(
            candidate,
            frequency,
            start_date=start_date,
        )
    while candidate in executed_dates:
        candidate = advance_execution_date(
            candidate,
            frequency,
            start_date=start_date,
        )
    if not is_execution_due(candidate, end_date=end_date):
        return None
    return candidate
