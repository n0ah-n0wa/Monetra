"""Unit tests for exchange-rate providers, cache, and failure handling."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from app.core.config import Settings
from app.domain.exchange_rate_provider import (
    ProviderUnavailableError,
    UnsupportedCurrencyPairError,
)
from app.domain.exchange_rates import convert_using_stored_rate
from app.services.exchange_rate_providers import (
    CachingExchangeRateProvider,
    InMemoryExchangeRateProvider,
    StaticExchangeRateProvider,
    UnavailableExchangeRateProvider,
    create_exchange_rate_provider,
    parse_static_rates,
)


class _FakeClock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now = self.now + timedelta(seconds=seconds)


@pytest.mark.asyncio
async def test_successful_retrieval_from_static_provider() -> None:
    provider = StaticExchangeRateProvider(
        {("EUR", "USD"): Decimal("1.10000000")},
        clock=_FakeClock(datetime(2026, 1, 15, tzinfo=UTC)),
    )
    quote = await provider.fetch_rate(
        base_currency="eur",
        quote_currency="usd",
        rate_date=date(2026, 1, 10),
    )
    assert quote.rate == Decimal("1.10000000")
    assert quote.base_currency == "EUR"
    assert quote.quote_currency == "USD"
    assert quote.rate_date == date(2026, 1, 10)
    assert quote.retrieved_at == datetime(2026, 1, 15, tzinfo=UTC)
    assert quote.source == "static"


@pytest.mark.asyncio
async def test_cache_hit_avoids_inner_provider_call() -> None:
    inner = InMemoryExchangeRateProvider()
    inner.set_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate="1.20000000",
        rate_date=date(2026, 2, 1),
    )
    clock = _FakeClock(datetime(2026, 2, 1, 12, 0, tzinfo=UTC))
    cached = CachingExchangeRateProvider(
        inner,
        ttl_seconds=60,
        clock=clock,
    )

    first = await cached.fetch_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate_date=date(2026, 2, 1),
    )
    second = await cached.fetch_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate_date=date(2026, 2, 1),
    )

    assert first.rate == second.rate == Decimal("1.20000000")
    assert inner.fetch_count == 1
    assert cached.hits == 1
    assert cached.misses == 1


@pytest.mark.asyncio
async def test_provider_failure_without_cache_raises() -> None:
    inner = InMemoryExchangeRateProvider()
    inner.force_unavailable = True
    cached = CachingExchangeRateProvider(inner, ttl_seconds=60)

    with pytest.raises(ProviderUnavailableError):
        await cached.fetch_rate(
            base_currency="EUR",
            quote_currency="USD",
            rate_date=date(2026, 3, 1),
        )


@pytest.mark.asyncio
async def test_stale_data_fallback_on_provider_failure() -> None:
    inner = InMemoryExchangeRateProvider()
    inner.set_rate(
        base_currency="GBP",
        quote_currency="USD",
        rate="1.30000000",
        rate_date=date(2026, 4, 1),
    )
    clock = _FakeClock(datetime(2026, 4, 1, 12, 0, tzinfo=UTC))
    cached = CachingExchangeRateProvider(
        inner,
        ttl_seconds=30,
        allow_stale_on_failure=True,
        clock=clock,
    )

    fresh = await cached.fetch_rate(
        base_currency="GBP",
        quote_currency="USD",
        rate_date=date(2026, 4, 1),
    )
    assert fresh.rate == Decimal("1.30000000")

    clock.advance(120)  # past TTL → stale
    inner.force_unavailable = True
    stale = await cached.fetch_rate(
        base_currency="GBP",
        quote_currency="USD",
        rate_date=date(2026, 4, 1),
    )
    assert stale.rate == Decimal("1.30000000")
    assert cached.stale_fallbacks == 1


@pytest.mark.asyncio
async def test_stale_entry_refetched_when_provider_recovers() -> None:
    inner = InMemoryExchangeRateProvider()
    inner.set_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate="1.10000000",
        rate_date=date(2026, 5, 1),
    )
    clock = _FakeClock(datetime(2026, 5, 1, 8, 0, tzinfo=UTC))
    cached = CachingExchangeRateProvider(inner, ttl_seconds=10, clock=clock)

    await cached.fetch_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate_date=date(2026, 5, 1),
    )
    clock.advance(20)
    inner.set_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate="1.15000000",
        rate_date=date(2026, 5, 1),
    )
    refreshed = await cached.fetch_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate_date=date(2026, 5, 1),
    )
    assert refreshed.rate == Decimal("1.15000000")
    assert inner.fetch_count == 2


@pytest.mark.asyncio
async def test_unsupported_currency_pair() -> None:
    provider = StaticExchangeRateProvider({("EUR", "USD"): Decimal("1.1")})
    with pytest.raises(UnsupportedCurrencyPairError) as exc:
        await provider.fetch_rate(
            base_currency="JPY",
            quote_currency="USD",
            rate_date=date(2026, 1, 1),
        )
    assert exc.value.code == "UNSUPPORTED_CURRENCY_PAIR"


@pytest.mark.asyncio
async def test_unavailable_provider() -> None:
    provider = UnavailableExchangeRateProvider()
    with pytest.raises(ProviderUnavailableError):
        await provider.fetch_rate(
            base_currency="EUR",
            quote_currency="USD",
            rate_date=date(2026, 1, 1),
        )


@pytest.mark.asyncio
async def test_test_provider_date_specific_rates() -> None:
    provider = InMemoryExchangeRateProvider()
    provider.set_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate="1.10000000",
        rate_date=date(2026, 1, 1),
    )
    provider.set_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate="1.20000000",
        rate_date=date(2026, 1, 10),
    )

    older = await provider.fetch_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate_date=date(2026, 1, 1),
    )
    newer = await provider.fetch_rate(
        base_currency="EUR",
        quote_currency="USD",
        rate_date=date(2026, 1, 10),
    )
    assert older.rate == Decimal("1.10000000")
    assert newer.rate == Decimal("1.20000000")


def test_deterministic_historical_conversion_uses_stored_rate() -> None:
    # Explicit stored rate for an as-of date — never a live provider call.
    money = convert_using_stored_rate(
        Decimal("100.0000"),
        from_currency="EUR",
        to_currency="USD",
        rate=Decimal("1.10000000"),
        as_of_date=date(2026, 1, 5),
    )
    assert money.amount == Decimal("110.0000")

    later_market = convert_using_stored_rate(
        Decimal("100.0000"),
        from_currency="EUR",
        to_currency="USD",
        rate=Decimal("1.10000000"),  # still the historical snapshot
        as_of_date=date(2026, 1, 5),
    )
    assert later_market.amount == Decimal("110.0000")


def test_parse_static_rates_and_factory() -> None:
    parsed = parse_static_rates("EUR:USD:1.1, GBP:USD:1.25")
    assert parsed[("EUR", "USD")] == Decimal("1.1")

    settings = Settings(
        exchange_rate_provider="static",
        exchange_rate_static_rates="EUR:USD:1.1",
        exchange_rate_cache_ttl_seconds=60,
        jwt_secret_key="test-secret-key-must-be-at-least-32-chars",
    )
    provider = create_exchange_rate_provider(settings)
    assert isinstance(provider, CachingExchangeRateProvider)


def test_factory_none_provider_without_cache() -> None:
    settings = Settings(
        exchange_rate_provider="none",
        exchange_rate_cache_ttl_seconds=0,
        jwt_secret_key="test-secret-key-must-be-at-least-32-chars",
    )
    provider = create_exchange_rate_provider(settings)
    assert isinstance(provider, UnavailableExchangeRateProvider)
