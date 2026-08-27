"""Exchange rate persistence for multi-currency reporting."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
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


async def get_rate_on_or_before(
    session: AsyncSession,
    *,
    base_currency: str,
    quote_currency: str,
    rate_date: date,
) -> ExchangeRate | None:
    if base_currency == quote_currency:
        return None
    result = await session.execute(
        select(ExchangeRate)
        .where(
            ExchangeRate.base_currency == base_currency,
            ExchangeRate.quote_currency == quote_currency,
            ExchangeRate.rate_date <= rate_date,
        )
        .order_by(ExchangeRate.rate_date.desc())
        .limit(1),
    )
    return result.scalar_one_or_none()


async def get_rate_for_date(
    session: AsyncSession,
    *,
    base_currency: str,
    quote_currency: str,
    rate_date: date,
) -> ExchangeRate | None:
    result = await session.execute(
        select(ExchangeRate).where(
            ExchangeRate.base_currency == base_currency,
            ExchangeRate.quote_currency == quote_currency,
            ExchangeRate.rate_date == rate_date,
        ),
    )
    return result.scalar_one_or_none()


async def insert_rate(
    session: AsyncSession,
    *,
    base_currency: str,
    quote_currency: str,
    rate: Decimal,
    rate_date: date,
    source: str | None,
) -> ExchangeRate:
    entity = ExchangeRate(
        base_currency=base_currency,
        quote_currency=quote_currency,
        rate=rate,
        rate_date=rate_date,
        source=source,
    )
    session.add(entity)
    await session.flush()
    return entity


async def list_rates(
    session: AsyncSession,
    *,
    base_currency: str | None,
    quote_currency: str | None,
    date_from: date | None,
    date_to: date | None,
    offset: int,
    limit: int,
) -> tuple[list[ExchangeRate], int]:
    filters = []
    if base_currency is not None:
        filters.append(ExchangeRate.base_currency == base_currency)
    if quote_currency is not None:
        filters.append(ExchangeRate.quote_currency == quote_currency)
    if date_from is not None:
        filters.append(ExchangeRate.rate_date >= date_from)
    if date_to is not None:
        filters.append(ExchangeRate.rate_date <= date_to)

    count_stmt = select(func.count()).select_from(ExchangeRate)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(await session.scalar(count_stmt) or 0)

    stmt = select(ExchangeRate)
    if filters:
        stmt = stmt.where(*filters)
    stmt = (
        stmt.order_by(
            ExchangeRate.rate_date.desc(),
            ExchangeRate.base_currency.asc(),
            ExchangeRate.quote_currency.asc(),
        )
        .offset(offset)
        .limit(limit)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return rows, total
