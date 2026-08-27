"""Exchange rate lookup tests for analytics conversion."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.models.exchange_rate import ExchangeRate
from app.repositories.exchange_rate_repository import get_rates_on_or_before_dates
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_rates_on_or_before_dates(db_session: AsyncSession) -> None:
    # Use obscure testing currencies so committed API seeds cannot collide.
    db_session.add_all(
        [
            ExchangeRate(
                base_currency="XTS",
                quote_currency="XAU",
                rate=Decimal("1.10000000"),
                rate_date=date(2026, 1, 1),
            ),
            ExchangeRate(
                base_currency="XTS",
                quote_currency="XAU",
                rate=Decimal("1.20000000"),
                rate_date=date(2026, 1, 10),
            ),
        ],
    )
    await db_session.flush()

    rates = await get_rates_on_or_before_dates(
        db_session,
        base_currency="XTS",
        quote_currency="XAU",
        dates={date(2026, 1, 5), date(2026, 1, 10), date(2026, 1, 15)},
    )
    assert rates[date(2026, 1, 5)] == Decimal("1.10000000")
    assert rates[date(2026, 1, 10)] == Decimal("1.20000000")
    assert rates[date(2026, 1, 15)] == Decimal("1.20000000")


@pytest.mark.asyncio
async def test_same_currency_returns_one(db_session: AsyncSession) -> None:
    rates = await get_rates_on_or_before_dates(
        db_session,
        base_currency="USD",
        quote_currency="USD",
        dates={date(2026, 1, 1)},
    )
    assert rates[date(2026, 1, 1)] == Decimal("1")


@pytest.mark.asyncio
async def test_missing_rate_before_first_snapshot_omits_date(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        ExchangeRate(
            base_currency="XPT",
            quote_currency="XPD",
            rate=Decimal("1.50000000"),
            rate_date=date(2026, 6, 1),
        ),
    )
    await db_session.flush()

    rates = await get_rates_on_or_before_dates(
        db_session,
        base_currency="XPT",
        quote_currency="XPD",
        dates={date(2026, 5, 1), date(2026, 6, 15)},
    )
    assert date(2026, 5, 1) not in rates
    assert rates[date(2026, 6, 15)] == Decimal("1.50000000")
