"""Exchange-rate domain rules for historical reporting conversions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.exceptions import ValidationAppError
from app.domain.currency import Money, convert_with_rate, normalize_currency
from app.domain.transfers import validate_exchange_rate


@dataclass(frozen=True, slots=True)
class RateQuote:
    """A dated FX quote: units of quote currency per 1 unit of base currency."""

    base_currency: str
    quote_currency: str
    rate: Decimal
    rate_date: date
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "base_currency",
            normalize_currency(self.base_currency),
        )
        object.__setattr__(
            self,
            "quote_currency",
            normalize_currency(self.quote_currency),
        )
        object.__setattr__(self, "rate", validate_exchange_rate(self.rate))
        if self.base_currency == self.quote_currency:
            raise ValidationAppError(
                code="INVALID_EXCHANGE_RATE",
                message="Base and quote currencies must be different.",
            )


def convert_using_stored_rate(
    amount: Decimal,
    *,
    from_currency: str,
    to_currency: str,
    rate: Decimal | None,
    as_of_date: date,
) -> Money:
    """Convert using a previously stored rate; never invent a live market rate.

    Same-currency conversions do not require a rate. Cross-currency conversion
    requires an explicit stored rate for historical integrity.
    """
    from_code = normalize_currency(from_currency)
    to_code = normalize_currency(to_currency)
    if from_code == to_code:
        return Money.of(amount, from_code)
    if rate is None:
        raise ValidationAppError(
            code="MISSING_EXCHANGE_RATE",
            message=(
                f"No exchange rate found for {from_code}/{to_code} "
                f"on or before {as_of_date.isoformat()}."
            ),
            details={
                "base_currency": from_code,
                "quote_currency": to_code,
                "as_of_date": as_of_date.isoformat(),
            },
        )
    return convert_with_rate(
        amount,
        rate=rate,
        from_currency=from_code,
        to_currency=to_code,
    )
