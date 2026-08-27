"""Currency codes and monetary amounts with exact decimal arithmetic."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app.core.exceptions import ValidationAppError
from app.domain.transactions import normalize_money

_CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class Currency:
    """ISO 4217 alphabetic currency code value object."""

    code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", normalize_currency(self.code))

    def __str__(self) -> str:
        return self.code


@dataclass(frozen=True, slots=True)
class Money:
    """Exact monetary amount in a specific currency."""

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", normalize_money(self.amount))
        if not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency(str(self.currency)))

    @classmethod
    def of(cls, amount: Decimal, currency: str | Currency) -> Money:
        return cls(
            amount=amount,
            currency=currency if isinstance(currency, Currency) else Currency(currency),
        )


def normalize_currency(currency: str) -> str:
    """Normalize and validate an ISO 4217 alphabetic currency code."""
    normalized = currency.strip().upper()
    if not _CURRENCY_CODE.fullmatch(normalized):
        raise ValidationAppError(
            code="INVALID_CURRENCY",
            message="Currency must be a three-letter ISO 4217 code.",
        )
    return normalized


def assert_same_currency(
    left: str | Currency,
    right: str | Currency,
    *,
    code: str = "CURRENCY_MISMATCH",
    message: str = "Currencies must match.",
) -> str:
    left_code = left.code if isinstance(left, Currency) else normalize_currency(left)
    right_code = (
        right.code if isinstance(right, Currency) else normalize_currency(right)
    )
    if left_code != right_code:
        raise ValidationAppError(code=code, message=message)
    return left_code


def convert_with_rate(
    amount: Decimal,
    *,
    rate: Decimal,
    from_currency: str | Currency,
    to_currency: str | Currency,
) -> Money:
    """Convert an amount using an explicit exchange rate (quote per 1 base)."""
    from_code = (
        from_currency.code
        if isinstance(from_currency, Currency)
        else normalize_currency(from_currency)
    )
    to_code = (
        to_currency.code
        if isinstance(to_currency, Currency)
        else normalize_currency(to_currency)
    )
    if from_code == to_code:
        return Money.of(amount, from_code)

    from app.domain.transfers import validate_exchange_rate

    validated_rate = validate_exchange_rate(rate)
    return Money.of(normalize_money(amount) * validated_rate, to_code)
