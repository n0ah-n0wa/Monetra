"""Currency domain tests."""

from decimal import Decimal

import pytest
from app.core.exceptions import ValidationAppError
from app.domain.currency import (
    Currency,
    Money,
    assert_same_currency,
    convert_with_rate,
    normalize_currency,
)


def test_normalize_currency() -> None:
    assert normalize_currency(" usd ") == "USD"


def test_normalize_currency_rejects_invalid() -> None:
    with pytest.raises(ValidationAppError, match="ISO 4217"):
        normalize_currency("US")


def test_currency_value_object() -> None:
    assert Currency("eur").code == "EUR"


def test_money_normalizes_amount() -> None:
    money = Money.of(Decimal("10.12345"), "USD")
    assert money.amount == Decimal("10.1234")
    assert money.currency.code == "USD"


def test_assert_same_currency() -> None:
    assert assert_same_currency("USD", Currency("usd")) == "USD"
    with pytest.raises(ValidationAppError) as exc:
        assert_same_currency("USD", "EUR")
    assert exc.value.code == "CURRENCY_MISMATCH"


def test_convert_with_rate_same_currency() -> None:
    money = convert_with_rate(
        Decimal("25.0000"),
        rate=Decimal("1.5"),
        from_currency="USD",
        to_currency="USD",
    )
    assert money.amount == Decimal("25.0000")
    assert money.currency.code == "USD"


def test_convert_with_rate_cross_currency_rounding() -> None:
    money = convert_with_rate(
        Decimal("100.0000"),
        rate=Decimal("1.23456789"),
        from_currency="EUR",
        to_currency="USD",
    )
    assert money.amount == Decimal("123.4568")
    assert money.currency.code == "USD"
