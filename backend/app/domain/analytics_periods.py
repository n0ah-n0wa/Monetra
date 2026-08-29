"""Analytics period preset resolution."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from enum import StrEnum

from app.core.exceptions import ValidationAppError


class AnalyticsPeriodPreset(StrEnum):
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    CURRENT_MONTH = "current_month"
    PREVIOUS_MONTH = "previous_month"
    CURRENT_YEAR = "current_year"
    PREVIOUS_YEAR = "previous_year"
    CUSTOM = "custom"


def resolve_analytics_period(
    *,
    preset: AnalyticsPeriodPreset,
    as_of_date: date,
    date_from: date | None,
    date_to: date | None,
    max_custom_period_days: int = 366,
) -> tuple[date, date]:
    if preset == AnalyticsPeriodPreset.CUSTOM:
        if date_from is None or date_to is None:
            raise ValidationAppError(
                code="INVALID_DATE_RANGE",
                message="Custom periods require date_from and date_to.",
            )
        if date_from > date_to:
            raise ValidationAppError(
                code="INVALID_DATE_RANGE",
                message="date_from must be on or before date_to.",
            )
        span_days = (date_to - date_from).days + 1
        if span_days > max_custom_period_days:
            raise ValidationAppError(
                code="INVALID_DATE_RANGE",
                message=(
                    "Custom analytics periods cannot exceed "
                    f"{max_custom_period_days} days."
                ),
                details={
                    "max_custom_period_days": max_custom_period_days,
                    "requested_days": span_days,
                },
            )
        return date_from, date_to

    if preset == AnalyticsPeriodPreset.LAST_7_DAYS:
        return as_of_date - timedelta(days=6), as_of_date
    if preset == AnalyticsPeriodPreset.LAST_30_DAYS:
        return as_of_date - timedelta(days=29), as_of_date
    if preset == AnalyticsPeriodPreset.LAST_90_DAYS:
        return as_of_date - timedelta(days=89), as_of_date

    if preset == AnalyticsPeriodPreset.CURRENT_MONTH:
        return date(as_of_date.year, as_of_date.month, 1), as_of_date

    if preset == AnalyticsPeriodPreset.PREVIOUS_MONTH:
        year = as_of_date.year
        month = as_of_date.month - 1
        if month == 0:
            month = 12
            year -= 1
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    if preset == AnalyticsPeriodPreset.CURRENT_YEAR:
        return date(as_of_date.year, 1, 1), as_of_date

    if preset == AnalyticsPeriodPreset.PREVIOUS_YEAR:
        year = as_of_date.year - 1
        return date(year, 1, 1), date(year, 12, 31)

    raise ValidationAppError(
        code="INVALID_ANALYTICS_PERIOD",
        message="Unsupported analytics period preset.",
    )


def resolve_previous_period(start_date: date, end_date: date) -> tuple[date, date]:
    """Return the immediately preceding period of equal length."""
    length_days = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=length_days - 1)
    return previous_start, previous_end


def resolve_comparison_period(
    *,
    preset: AnalyticsPeriodPreset,
    start_date: date,
    end_date: date,
    as_of_date: date,
) -> tuple[date, date]:
    """Resolve the comparison window for period-over-period analytics.

    Calendar presets compare against the prior calendar month/year (SPEC §20).
    Rolling and custom presets use an equal-length preceding window.
    """
    if preset == AnalyticsPeriodPreset.CURRENT_MONTH:
        return resolve_analytics_period(
            preset=AnalyticsPeriodPreset.PREVIOUS_MONTH,
            as_of_date=as_of_date,
            date_from=None,
            date_to=None,
        )
    if preset == AnalyticsPeriodPreset.PREVIOUS_MONTH:
        return resolve_analytics_period(
            preset=AnalyticsPeriodPreset.PREVIOUS_MONTH,
            as_of_date=start_date,
            date_from=None,
            date_to=None,
        )
    if preset == AnalyticsPeriodPreset.CURRENT_YEAR:
        return resolve_analytics_period(
            preset=AnalyticsPeriodPreset.PREVIOUS_YEAR,
            as_of_date=as_of_date,
            date_from=None,
            date_to=None,
        )
    if preset == AnalyticsPeriodPreset.PREVIOUS_YEAR:
        year = start_date.year - 1
        return date(year, 1, 1), date(year, 12, 31)
    return resolve_previous_period(start_date, end_date)


def trend_granularity(start_date: date, end_date: date) -> str:
    """Choose day, week, or month buckets based on period length."""
    length_days = (end_date - start_date).days + 1
    if length_days <= 31:
        return "day"
    if length_days <= 180:
        return "week"
    return "month"


def bucket_date(value: date, granularity: str) -> date:
    if granularity == "day":
        return value
    if granularity == "week":
        return value - timedelta(days=value.weekday())
    return date(value.year, value.month, 1)


def iter_dates(start_date: date, end_date: date) -> list[date]:
    current = start_date
    dates: list[date] = []
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates
