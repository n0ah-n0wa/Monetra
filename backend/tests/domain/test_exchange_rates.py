"""Exchange-rate domain conversion tests."""

from datetime import date
from decimal import Decimal

import pytest
from app.core.exceptions import ValidationAppError
from app.domain.exchange_rates import RateQuote, convert_using_stored_rate


def test_rate_quote_rejects_same_currency() -> None:
    with pytest.raises(ValidationAppError):
        RateQuote(
            base_currency="USD",
            quote_currency="USD",
            rate=Decimal("1.0"),
            rate_date=date(2026, 1, 1),
        )


def test_convert_using_stored_rate_same_currency() -> None:
    money = convert_using_stored_rate(
        Decimal("40.0000"),
        from_currency="USD",
        to_currency="USD",
        rate=None,
        as_of_date=date(2026, 1, 1),
    )
    assert money.amount == Decimal("40.0000")


def test_convert_using_stored_rate_requires_rate() -> None:
    with pytest.raises(ValidationAppError) as exc:
        convert_using_stored_rate(
            Decimal("40.0000"),
            from_currency="EUR",
            to_currency="USD",
            rate=None,
            as_of_date=date(2026, 1, 1),
        )
    assert exc.value.code == "MISSING_EXCHANGE_RATE"


def test_convert_using_historical_rate() -> None:
    money = convert_using_stored_rate(
        Decimal("50.0000"),
        from_currency="EUR",
        to_currency="USD",
        rate=Decimal("1.10000000"),
        as_of_date=date(2026, 1, 1),
    )
    assert money.amount == Decimal("55.0000")
