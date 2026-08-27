"""Exchange rate persistence for analytics conversion."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_rate import ExchangeRate


async def get_rates_on_or_before_dates(
    session: AsyncSession,
    *,
    base_currency: str,
    quote_currency: str,
    dates: set[date],
) -> dict[date, Decimal]:
    if base_currency == quote_currency:
        return dict.fromkeys(dates, Decimal("1"))

    if not dates:
        return {}

    max_date = max(dates)
    result = await session.execute(
        select(ExchangeRate.rate_date, ExchangeRate.rate)
        .where(
            ExchangeRate.base_currency == base_currency,
            ExchangeRate.quote_currency == quote_currency,
            ExchangeRate.rate_date <= max_date,
        )
        .order_by(ExchangeRate.rate_date.asc()),
    )
    rows = list(result.all())
    if not rows:
        return {}

    rates: dict[date, Decimal] = {}
    latest_rate: Decimal | None = None
    row_index = 0
    for target in sorted(dates):
        while row_index < len(rows) and rows[row_index][0] <= target:
            latest_rate = Decimal(rows[row_index][1])
            row_index += 1
        if latest_rate is not None:
            rates[target] = latest_rate
    return rates
