"""Shared PostgreSQL column types."""

from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.types import TypeDecorator

# NUMERIC(19, 4) supports values up to 999,999,999,999,999.9999 exactly.
MONEY_PRECISION = 19
MONEY_SCALE = 4

# Exchange rates may require higher precision.
EXCHANGE_RATE_PRECISION = 19
EXCHANGE_RATE_SCALE = 8


class MoneyNumeric(TypeDecorator[Decimal]):
    """Exact decimal storage for monetary amounts."""

    impl = Numeric
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(precision=MONEY_PRECISION, scale=MONEY_SCALE)

    def process_bind_param(
        self,
        value: Decimal | None,
        dialect: object,
    ) -> Decimal | None:
        return value

    def process_result_value(
        self,
        value: Decimal | None,
        dialect: object,
    ) -> Decimal | None:
        return value


class ExchangeRateNumeric(TypeDecorator[Decimal]):
    """Exact decimal storage for exchange rates."""

    impl = Numeric
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(
            precision=EXCHANGE_RATE_PRECISION,
            scale=EXCHANGE_RATE_SCALE,
        )

    def process_bind_param(
        self,
        value: Decimal | None,
        dialect: object,
    ) -> Decimal | None:
        return value

    def process_result_value(
        self,
        value: Decimal | None,
        dialect: object,
    ) -> Decimal | None:
        return value
