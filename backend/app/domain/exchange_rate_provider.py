"""Exchange-rate provider abstraction (SPEC §23).

Dashboard and analytics read stored snapshots only. Providers are used when
explicitly fetching rates to persist; they must never be required on every
dashboard request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from app.core.exceptions import AppError, ValidationAppError
from app.domain.currency import normalize_currency
from app.domain.transfers import validate_exchange_rate


@dataclass(frozen=True, slots=True)
class ProviderRateQuote:
    """Timestamped FX quote returned by an external provider."""

    base_currency: str
    quote_currency: str
    rate: Decimal
    rate_date: date
    retrieved_at: datetime
    source: str

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


class ExchangeRateProvider(Protocol):
    """External FX source isolated behind a stable, swappable interface."""

    async def fetch_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate_date: date,
    ) -> ProviderRateQuote:
        """Return a timestamped quote (quote currency units per 1 base unit)."""


class ProviderUnavailableError(AppError):
    def __init__(
        self,
        *,
        message: str = "Exchange-rate provider is unavailable.",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            code="EXCHANGE_RATE_PROVIDER_UNAVAILABLE",
            message=message,
            status_code=503,
            details=details,
        )


class UnsupportedCurrencyPairError(AppError):
    def __init__(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        message: str | None = None,
    ) -> None:
        super().__init__(
            code="UNSUPPORTED_CURRENCY_PAIR",
            message=message
            or (
                f"Exchange-rate provider does not support "
                f"{base_currency}/{quote_currency}."
            ),
            status_code=422,
            details={
                "base_currency": base_currency,
                "quote_currency": quote_currency,
            },
        )
