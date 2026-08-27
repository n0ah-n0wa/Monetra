"""Analytics domain calculation tests."""

from decimal import Decimal

from app.domain.analytics import (
    compute_net_cash_flow,
    compute_period_change,
    compute_period_change_percent,
    compute_savings_rate,
)


def test_compute_net_cash_flow() -> None:
    assert compute_net_cash_flow(
        income=Decimal("1000.0000"),
        expenses=Decimal("400.0000"),
    ) == Decimal("600.0000")


def test_compute_savings_rate() -> None:
    assert compute_savings_rate(
        income=Decimal("1000.0000"),
        expenses=Decimal("400.0000"),
    ) == Decimal("60.0000")


def test_compute_savings_rate_negative_when_overspending() -> None:
    assert compute_savings_rate(
        income=Decimal("100.0000"),
        expenses=Decimal("150.0000"),
    ) == Decimal("-50.0000")


def test_compute_period_change() -> None:
    assert compute_period_change(
        current=Decimal("500.0000"),
        previous=Decimal("400.0000"),
    ) == Decimal("100.0000")


def test_compute_period_change_percent() -> None:
    assert compute_period_change_percent(
        current=Decimal("500.0000"),
        previous=Decimal("400.0000"),
    ) == Decimal("25.0000")


def test_compute_period_change_percent_zero_previous_returns_none() -> None:
    assert (
        compute_period_change_percent(
            current=Decimal("100.0000"),
            previous=Decimal("0"),
        )
        is None
    )
