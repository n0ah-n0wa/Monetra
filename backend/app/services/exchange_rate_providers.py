"""Exchange-rate provider implementations, caching, and factory."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.currency import normalize_currency
from app.domain.exchange_rate_provider import (
    ExchangeRateProvider,
    ProviderRateQuote,
    ProviderUnavailableError,
    UnsupportedCurrencyPairError,
)
from app.domain.transfers import validate_exchange_rate

logger = get_logger(__name__)

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    quote: ProviderRateQuote
    cached_at: datetime


class CachingExchangeRateProvider:
    """In-memory TTL cache wrapping any provider.

    Fresh hits avoid remote calls. On provider failure, optionally returns a
    previously cached (stale) quote so callers can degrade gracefully without
    coupling dashboards to live FX availability.
    """

    def __init__(
        self,
        inner: ExchangeRateProvider,
        *,
        ttl_seconds: int,
        allow_stale_on_failure: bool = True,
        clock: Clock | None = None,
    ) -> None:
        if ttl_seconds < 0:
            msg = "ttl_seconds must be >= 0"
            raise ValueError(msg)
        self._inner = inner
        self._ttl = timedelta(seconds=ttl_seconds)
        self._allow_stale_on_failure = allow_stale_on_failure
        self._clock = clock or _utc_now
        self._cache: dict[tuple[str, str, date], _CacheEntry] = {}
        self.hits = 0
        self.misses = 0
        self.stale_fallbacks = 0

    def clear(self) -> None:
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        self.stale_fallbacks = 0

    def _is_fresh(self, entry: _CacheEntry, now: datetime) -> bool:
        if self._ttl == timedelta(0):
            return False
        return now - entry.cached_at <= self._ttl

    async def fetch_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate_date: date,
    ) -> ProviderRateQuote:
        base = normalize_currency(base_currency)
        quote = normalize_currency(quote_currency)
        key = (base, quote, rate_date)
        now = self._clock()
        entry = self._cache.get(key)

        if entry is not None and self._is_fresh(entry, now):
            self.hits += 1
            return entry.quote

        self.misses += 1
        try:
            fetched = await self._inner.fetch_rate(
                base_currency=base,
                quote_currency=quote,
                rate_date=rate_date,
            )
        except (ProviderUnavailableError, UnsupportedCurrencyPairError):
            if self._allow_stale_on_failure and entry is not None:
                self.stale_fallbacks += 1
                logger.warning(
                    "event=exchange_rate_stale_fallback pair=%s/%s date=%s",
                    base,
                    quote,
                    rate_date.isoformat(),
                )
                return entry.quote
            raise

        self._cache[key] = _CacheEntry(quote=fetched, cached_at=now)
        return fetched


class StaticExchangeRateProvider:
    """Configurable static rates for development (no network, no secrets)."""

    def __init__(
        self,
        rates: dict[tuple[str, str], Decimal] | None = None,
        *,
        source: str = "static",
        clock: Clock | None = None,
    ) -> None:
        self._rates = {
            (
                normalize_currency(base),
                normalize_currency(quote),
            ): validate_exchange_rate(
                rate,
            )
            for (base, quote), rate in (rates or {}).items()
        }
        self._source = source
        self._clock = clock or _utc_now

    async def fetch_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate_date: date,
    ) -> ProviderRateQuote:
        base = normalize_currency(base_currency)
        quote = normalize_currency(quote_currency)
        key = (base, quote)
        if key not in self._rates:
            raise UnsupportedCurrencyPairError(
                base_currency=base,
                quote_currency=quote,
            )
        return ProviderRateQuote(
            base_currency=base,
            quote_currency=quote,
            rate=self._rates[key],
            rate_date=rate_date,
            retrieved_at=self._clock(),
            source=self._source,
        )


class InMemoryExchangeRateProvider:
    """Deterministic test provider with call counting and failure injection."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._rates: dict[tuple[str, str, date], Decimal] = {}
        self._pair_defaults: dict[tuple[str, str], Decimal] = {}
        self._clock = clock or _utc_now
        self.fetch_count = 0
        self.fail_next = False
        self.force_unavailable = False

    def clear(self) -> None:
        self._rates.clear()
        self._pair_defaults.clear()
        self.fetch_count = 0
        self.fail_next = False
        self.force_unavailable = False

    def set_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate: Decimal | str,
        rate_date: date | None = None,
    ) -> None:
        base = normalize_currency(base_currency)
        quote = normalize_currency(quote_currency)
        value = validate_exchange_rate(Decimal(rate))
        if rate_date is None:
            self._pair_defaults[(base, quote)] = value
        else:
            self._rates[(base, quote, rate_date)] = value

    async def fetch_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate_date: date,
    ) -> ProviderRateQuote:
        self.fetch_count += 1
        base = normalize_currency(base_currency)
        quote = normalize_currency(quote_currency)

        if self.force_unavailable or self.fail_next:
            self.fail_next = False
            raise ProviderUnavailableError(
                message="Test exchange-rate provider forced failure.",
            )

        rate = self._rates.get((base, quote, rate_date))
        if rate is None:
            rate = self._pair_defaults.get((base, quote))
        if rate is None:
            raise UnsupportedCurrencyPairError(
                base_currency=base,
                quote_currency=quote,
            )

        return ProviderRateQuote(
            base_currency=base,
            quote_currency=quote,
            rate=rate,
            rate_date=rate_date,
            retrieved_at=self._clock(),
            source="test",
        )


class UnavailableExchangeRateProvider:
    """Fallback when no external provider is configured."""

    async def fetch_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate_date: date,
    ) -> ProviderRateQuote:
        del rate_date
        raise ProviderUnavailableError(
            details={
                "base_currency": normalize_currency(base_currency),
                "quote_currency": normalize_currency(quote_currency),
            },
        )


def parse_static_rates(raw: str) -> dict[tuple[str, str], Decimal]:
    """Parse ``EUR:USD:1.1,GBP:USD:1.25`` style configuration (no secrets)."""
    rates: dict[tuple[str, str], Decimal] = {}
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) != 3:
            continue
        base, quote, rate_text = (part.strip().upper() for part in parts)
        rates[(base, quote)] = Decimal(rate_text)
    return rates


def create_exchange_rate_provider(settings: Settings) -> ExchangeRateProvider:
    """Build the configured provider, optionally wrapped with a TTL cache."""
    if settings.exchange_rate_provider == "static":
        inner: ExchangeRateProvider = StaticExchangeRateProvider(
            parse_static_rates(settings.exchange_rate_static_rates),
        )
    elif settings.exchange_rate_provider == "test":
        inner = InMemoryExchangeRateProvider()
    else:
        inner = UnavailableExchangeRateProvider()

    if settings.exchange_rate_cache_ttl_seconds <= 0:
        return inner

    return CachingExchangeRateProvider(
        inner,
        ttl_seconds=settings.exchange_rate_cache_ttl_seconds,
        allow_stale_on_failure=settings.exchange_rate_allow_stale_on_failure,
    )


def unwrap_exchange_rate_provider(
    provider: ExchangeRateProvider,
) -> ExchangeRateProvider:
    """Return the inner provider when a caching wrapper is present."""
    if isinstance(provider, CachingExchangeRateProvider):
        return provider._inner
    return provider


def get_exchange_rate_provider(application: object) -> ExchangeRateProvider:
    state = getattr(application, "state", None)
    provider = (
        getattr(state, "exchange_rate_provider", None) if state is not None else None
    )
    if isinstance(
        provider,
        (
            CachingExchangeRateProvider,
            StaticExchangeRateProvider,
            InMemoryExchangeRateProvider,
            UnavailableExchangeRateProvider,
        ),
    ):
        return provider
    return UnavailableExchangeRateProvider()
