"""Transfer domain rule tests."""

from decimal import Decimal

import pytest
from app.core.exceptions import ValidationAppError
from app.domain.transfers import (
    assert_sufficient_balance,
    compute_destination_amount,
    resolve_transfer_amounts,
)


def test_same_currency_transfer_preserves_exact_amount() -> None:
    source, destination, rate = resolve_transfer_amounts(
        source_currency="USD",
        destination_currency="USD",
        source_amount=Decimal("250.5000"),
        destination_amount=None,
        exchange_rate=None,
    )
    assert source == Decimal("250.5000")
    assert destination == Decimal("250.5000")
    assert rate is None


def test_cross_currency_transfer_with_exchange_rate() -> None:
    source, destination, rate = resolve_transfer_amounts(
        source_currency="USD",
        destination_currency="EUR",
        source_amount=Decimal("100.0000"),
        destination_amount=None,
        exchange_rate=Decimal("0.85000000"),
    )
    assert source == Decimal("100.0000")
    assert destination == Decimal("85.0000")
    assert rate == Decimal("0.85000000")


def test_cross_currency_rejects_mismatched_destination_amount() -> None:
    with pytest.raises(ValidationAppError) as exc:
        resolve_transfer_amounts(
            source_currency="USD",
            destination_currency="EUR",
            source_amount=Decimal("100.0000"),
            destination_amount=Decimal("90.0000"),
            exchange_rate=Decimal("0.85000000"),
        )
    assert exc.value.code == "TRANSFER_AMOUNT_MISMATCH"


def test_assert_sufficient_balance() -> None:
    assert_sufficient_balance(Decimal("100.0000"), Decimal("99.9999"))
    with pytest.raises(ValidationAppError) as exc:
        assert_sufficient_balance(Decimal("100.0000"), Decimal("100.0001"))
    assert exc.value.code == "INSUFFICIENT_BALANCE"


def test_compute_destination_amount_uses_decimal_math() -> None:
    result = compute_destination_amount(
        Decimal("100.0000"),
        Decimal("1.23456789"),
    )
    assert result == Decimal("123.4568")
