"""Analytics period preset resolution tests."""

from datetime import date

import pytest
from app.core.exceptions import ValidationAppError
from app.domain.analytics_periods import (
    AnalyticsPeriodPreset,
    bucket_date,
    resolve_analytics_period,
    resolve_comparison_period,
    resolve_previous_period,
    trend_granularity,
)


def test_resolve_last_7_days() -> None:
    start, end = resolve_analytics_period(
        preset=AnalyticsPeriodPreset.LAST_7_DAYS,
        as_of_date=date(2026, 1, 15),
        date_from=None,
        date_to=None,
    )
    assert start == date(2026, 1, 9)
    assert end == date(2026, 1, 15)


def test_resolve_last_30_days() -> None:
    start, end = resolve_analytics_period(
        preset=AnalyticsPeriodPreset.LAST_30_DAYS,
        as_of_date=date(2026, 1, 31),
        date_from=None,
        date_to=None,
    )
    assert start == date(2026, 1, 2)
    assert end == date(2026, 1, 31)


def test_resolve_current_month() -> None:
    start, end = resolve_analytics_period(
        preset=AnalyticsPeriodPreset.CURRENT_MONTH,
        as_of_date=date(2026, 3, 20),
        date_from=None,
        date_to=None,
    )
    assert start == date(2026, 3, 1)
    assert end == date(2026, 3, 20)


def test_resolve_previous_month() -> None:
    start, end = resolve_analytics_period(
        preset=AnalyticsPeriodPreset.PREVIOUS_MONTH,
        as_of_date=date(2026, 3, 20),
        date_from=None,
        date_to=None,
    )
    assert start == date(2026, 2, 1)
    assert end == date(2026, 2, 28)


def test_resolve_current_year() -> None:
    start, end = resolve_analytics_period(
        preset=AnalyticsPeriodPreset.CURRENT_YEAR,
        as_of_date=date(2026, 6, 10),
        date_from=None,
        date_to=None,
    )
    assert start == date(2026, 1, 1)
    assert end == date(2026, 6, 10)


def test_resolve_previous_year() -> None:
    start, end = resolve_analytics_period(
        preset=AnalyticsPeriodPreset.PREVIOUS_YEAR,
        as_of_date=date(2026, 6, 10),
        date_from=None,
        date_to=None,
    )
    assert start == date(2025, 1, 1)
    assert end == date(2025, 12, 31)


def test_resolve_custom_period() -> None:
    start, end = resolve_analytics_period(
        preset=AnalyticsPeriodPreset.CUSTOM,
        as_of_date=date(2026, 6, 10),
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )
    assert start == date(2026, 1, 1)
    assert end == date(2026, 1, 31)


def test_custom_period_requires_dates() -> None:
    with pytest.raises(ValidationAppError, match="date_from"):
        resolve_analytics_period(
            preset=AnalyticsPeriodPreset.CUSTOM,
            as_of_date=date(2026, 1, 15),
            date_from=None,
            date_to=date(2026, 1, 31),
        )


def test_custom_period_rejects_inverted_range() -> None:
    with pytest.raises(ValidationAppError, match="date_from"):
        resolve_analytics_period(
            preset=AnalyticsPeriodPreset.CUSTOM,
            as_of_date=date(2026, 1, 15),
            date_from=date(2026, 2, 1),
            date_to=date(2026, 1, 31),
        )


def test_custom_period_rejects_excessive_span() -> None:
    with pytest.raises(ValidationAppError, match="366"):
        resolve_analytics_period(
            preset=AnalyticsPeriodPreset.CUSTOM,
            as_of_date=date(2026, 12, 31),
            date_from=date(2026, 1, 1),
            date_to=date(2027, 1, 2),
            max_custom_period_days=366,
        )


def test_resolve_previous_period_equal_length() -> None:
    start, end = resolve_previous_period(date(2026, 1, 10), date(2026, 1, 20))
    assert (end - start).days == (date(2026, 1, 20) - date(2026, 1, 10)).days
    assert end == date(2026, 1, 9)


def test_resolve_comparison_period_current_month_uses_previous_calendar_month() -> None:
    start, end = resolve_comparison_period(
        preset=AnalyticsPeriodPreset.CURRENT_MONTH,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 15),
        as_of_date=date(2026, 3, 15),
    )
    assert start == date(2026, 2, 1)
    assert end == date(2026, 2, 28)


def test_resolve_comparison_period_current_year_uses_previous_calendar_year() -> None:
    start, end = resolve_comparison_period(
        preset=AnalyticsPeriodPreset.CURRENT_YEAR,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 10),
        as_of_date=date(2026, 6, 10),
    )
    assert start == date(2025, 1, 1)
    assert end == date(2025, 12, 31)


def test_resolve_comparison_period_rolling_uses_equal_length() -> None:
    start, end = resolve_comparison_period(
        preset=AnalyticsPeriodPreset.LAST_7_DAYS,
        start_date=date(2026, 1, 9),
        end_date=date(2026, 1, 15),
        as_of_date=date(2026, 1, 15),
    )
    assert start == date(2026, 1, 2)
    assert end == date(2026, 1, 8)


def test_trend_granularity() -> None:
    assert trend_granularity(date(2026, 1, 1), date(2026, 1, 20)) == "day"
    assert trend_granularity(date(2026, 1, 1), date(2026, 4, 1)) == "week"
    assert trend_granularity(date(2026, 1, 1), date(2026, 12, 31)) == "month"


def test_bucket_date_week_starts_monday() -> None:
    assert bucket_date(date(2026, 1, 14), "week") == date(2026, 1, 12)
