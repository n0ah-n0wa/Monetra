"""Exchange-rate orchestration: store, lookup, convert, optional provider fetch."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, ValidationAppError
from app.domain.currency import Money, normalize_currency
from app.domain.exchange_rate_provider import (
    ExchangeRateProvider,
    ProviderUnavailableError,
    UnsupportedCurrencyPairError,
)
from app.domain.exchange_rates import RateQuote, convert_using_stored_rate
from app.domain.transfers import validate_exchange_rate
from app.models.exchange_rate import ExchangeRate
from app.repositories import exchange_rate_repository as rate_repo
from app.schemas.exchange_rates import ExchangeRateResponse
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)


def _to_response(entity: ExchangeRate) -> ExchangeRateResponse:
    return ExchangeRateResponse(
        id=str(entity.id),
        base_currency=entity.base_currency,
        quote_currency=entity.quote_currency,
        rate=entity.rate,
        rate_date=entity.rate_date,
        source=entity.source,
        retrieved_at=entity.created_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


async def store_rate(
    session: AsyncSession,
    *,
    base_currency: str,
    quote_currency: str,
    rate: Decimal,
    rate_date: date,
    source: str | None = "manual",
    overwrite_existing: bool = False,
) -> ExchangeRateResponse:
    """Persist a dated rate snapshot.

    Historical snapshots are immutable by default. Overwrite requires an
    explicit ``overwrite_existing=True`` product decision so newly fetched
    rates never silently rewrite past analytics.
    """
    quote = RateQuote(
        base_currency=base_currency,
        quote_currency=quote_currency,
        rate=rate,
        rate_date=rate_date,
        source=source,
    )
    existing = await rate_repo.get_rate_for_date(
        session,
        base_currency=quote.base_currency,
        quote_currency=quote.quote_currency,
        rate_date=quote.rate_date,
    )
    if existing is not None:
        if not overwrite_existing:
            raise ConflictError(
                code="EXCHANGE_RATE_EXISTS",
                message=(
                    "An exchange rate already exists for this pair and date. "
                    "Historical rates are not overwritten unless explicitly requested."
                ),
                details={
                    "base_currency": quote.base_currency,
                    "quote_currency": quote.quote_currency,
                    "rate_date": quote.rate_date.isoformat(),
                },
            )
        existing.rate = quote.rate
        existing.source = quote.source
        await session.flush()
        await session.commit()
        await session.refresh(existing)
        return _to_response(existing)

    entity = await rate_repo.insert_rate(
        session,
        base_currency=quote.base_currency,
        quote_currency=quote.quote_currency,
        rate=quote.rate,
        rate_date=quote.rate_date,
        source=quote.source,
    )
    await session.commit()
    await session.refresh(entity)
    return _to_response(entity)


async def get_stored_rate(
    session: AsyncSession,
    *,
    base_currency: str,
    quote_currency: str,
    rate_date: date,
    require_exact_date: bool = False,
) -> ExchangeRateResponse:
    base = normalize_currency(base_currency)
    quote = normalize_currency(quote_currency)
    if base == quote:
        raise ValidationAppError(
            code="INVALID_EXCHANGE_RATE",
            message="Base and quote currencies must be different.",
        )
    if require_exact_date:
        entity = await rate_repo.get_rate_for_date(
            session,
            base_currency=base,
            quote_currency=quote,
            rate_date=rate_date,
        )
    else:
        entity = await rate_repo.get_rate_on_or_before(
            session,
            base_currency=base,
            quote_currency=quote,
            rate_date=rate_date,
        )
    if entity is None:
        raise ValidationAppError(
            code="MISSING_EXCHANGE_RATE",
            message=(
                f"No exchange rate found for {base}/{quote} "
                f"on or before {rate_date.isoformat()}."
            ),
            details={
                "base_currency": base,
                "quote_currency": quote,
                "rate_date": rate_date.isoformat(),
            },
        )
    return _to_response(entity)


async def list_stored_rates(
    session: AsyncSession,
    *,
    settings: Settings,
    page: int,
    page_size: int | None,
    base_currency: str | None,
    quote_currency: str | None,
    date_from: date | None,
    date_to: date | None,
) -> PaginatedResponse[ExchangeRateResponse]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size or settings.api_default_page_size,
        max_page_size=settings.api_max_page_size,
    )
    base = normalize_currency(base_currency) if base_currency else None
    quote = normalize_currency(quote_currency) if quote_currency else None
    rows, total = await rate_repo.list_rates(
        session,
        base_currency=base,
        quote_currency=quote,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=[_to_response(row) for row in rows],
        page=page,
        page_size=limit,
        total_items=total,
    )


async def convert_amount(
    session: AsyncSession,
    *,
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    as_of_date: date,
) -> Money:
    """Convert using stored historical rates only (never a live provider call)."""
    from_code = normalize_currency(from_currency)
    to_code = normalize_currency(to_currency)
    if from_code == to_code:
        return Money.of(amount, from_code)

    rates = await rate_repo.get_rates_on_or_before_dates(
        session,
        base_currency=from_code,
        quote_currency=to_code,
        dates={as_of_date},
    )
    return convert_using_stored_rate(
        amount,
        from_currency=from_code,
        to_currency=to_code,
        rate=rates.get(as_of_date),
        as_of_date=as_of_date,
    )


async def fetch_and_store_rate(
    session: AsyncSession,
    *,
    provider: ExchangeRateProvider,
    base_currency: str,
    quote_currency: str,
    rate_date: date | None = None,
    overwrite_existing: bool = False,
) -> ExchangeRateResponse:
    """Fetch from the configured provider and store a dated snapshot.

    Defaults to refusing overwrite so historical analytics remain stable when
    a provider later publishes a different value for the same date.
    """
    effective_date = rate_date or datetime.now(UTC).date()
    base = normalize_currency(base_currency)
    quote = normalize_currency(quote_currency)
    if base == quote:
        raise ValidationAppError(
            code="INVALID_EXCHANGE_RATE",
            message="Base and quote currencies must be different.",
        )
    try:
        fetched = await provider.fetch_rate(
            base_currency=base,
            quote_currency=quote,
            rate_date=effective_date,
        )
    except (ProviderUnavailableError, UnsupportedCurrencyPairError):
        raise
    rate = validate_exchange_rate(fetched.rate)
    return await store_rate(
        session,
        base_currency=fetched.base_currency,
        quote_currency=fetched.quote_currency,
        rate=rate,
        rate_date=fetched.rate_date,
        source=fetched.source,
        overwrite_existing=overwrite_existing,
    )


async def build_rate_lookup(
    session: AsyncSession,
    *,
    reporting_currency: str,
    pairs: set[tuple[str, date]],
) -> dict[tuple[str, date], Decimal]:
    """Build (currency, date) → rate lookup for reporting conversion."""
    reporting = normalize_currency(reporting_currency)
    lookup: dict[tuple[str, date], Decimal] = {}
    by_currency: dict[str, set[date]] = {}
    for currency, rate_date in pairs:
        code = normalize_currency(currency)
        if code == reporting:
            lookup[(code, rate_date)] = Decimal("1")
            continue
        by_currency.setdefault(code, set()).add(rate_date)

    for currency, dates in by_currency.items():
        rates = await rate_repo.get_rates_on_or_before_dates(
            session,
            base_currency=currency,
            quote_currency=reporting,
            dates=dates,
        )
        missing = sorted(value for value in dates if value not in rates)
        if missing:
            raise ValidationAppError(
                code="MISSING_EXCHANGE_RATE",
                message=(
                    f"No exchange rate found for {currency}/{reporting} "
                    f"on or before {missing[0].isoformat()}."
                ),
                details={
                    "base_currency": currency,
                    "quote_currency": reporting,
                    "missing_dates": [value.isoformat() for value in missing],
                },
            )
        for rate_date in dates:
            lookup[(currency, rate_date)] = rates[rate_date]
    return lookup


def convert_amount_with_lookup(
    *,
    amount: Decimal,
    currency: str,
    rate_date: date,
    reporting_currency: str,
    rate_lookup: dict[tuple[str, date], Decimal],
) -> Decimal:
    from_code = normalize_currency(currency)
    to_code = normalize_currency(reporting_currency)
    if from_code == to_code:
        return Money.of(amount, from_code).amount
    rate = rate_lookup.get((from_code, rate_date))
    return convert_using_stored_rate(
        amount,
        from_currency=from_code,
        to_currency=to_code,
        rate=rate,
        as_of_date=rate_date,
    ).amount
