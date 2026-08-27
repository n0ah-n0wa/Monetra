"""Exchange rate endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.schemas.exchange_rates import (
    ConvertAmountRequest,
    ConvertAmountResponse,
    ExchangeRateCreateRequest,
    ExchangeRateFetchRequest,
    ExchangeRateResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.services import exchange_rate_service
from app.services.exchange_rate_providers import get_exchange_rate_provider

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.post(
    "",
    response_model=ExchangeRateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exchange_rate(
    payload: ExchangeRateCreateRequest,
    session: SessionDep,
    _current_user: CurrentUserDep,
) -> ExchangeRateResponse:
    return await exchange_rate_service.store_rate(
        session,
        base_currency=payload.base_currency,
        quote_currency=payload.quote_currency,
        rate=payload.rate,
        rate_date=payload.rate_date,
        source=payload.source,
        overwrite_existing=payload.overwrite_existing,
    )


@router.get("", response_model=PaginatedResponse[ExchangeRateResponse])
async def list_exchange_rates(
    session: SessionDep,
    settings: SettingsDep,
    _current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    base_currency: str | None = None,
    quote_currency: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> PaginatedResponse[ExchangeRateResponse]:
    return await exchange_rate_service.list_stored_rates(
        session,
        settings=settings,
        page=page,
        page_size=page_size,
        base_currency=base_currency,
        quote_currency=quote_currency,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/lookup", response_model=ExchangeRateResponse)
async def lookup_exchange_rate(
    session: SessionDep,
    _current_user: CurrentUserDep,
    base_currency: str,
    quote_currency: str,
    rate_date: date,
    exact: bool = False,
) -> ExchangeRateResponse:
    return await exchange_rate_service.get_stored_rate(
        session,
        base_currency=base_currency,
        quote_currency=quote_currency,
        rate_date=rate_date,
        require_exact_date=exact,
    )


@router.post("/convert", response_model=ConvertAmountResponse)
async def convert_amount(
    payload: ConvertAmountRequest,
    session: SessionDep,
    _current_user: CurrentUserDep,
) -> ConvertAmountResponse:
    money = await exchange_rate_service.convert_amount(
        session,
        amount=payload.amount,
        from_currency=payload.from_currency,
        to_currency=payload.to_currency,
        as_of_date=payload.as_of_date,
    )
    rate_used = None
    if payload.from_currency != payload.to_currency:
        stored = await exchange_rate_service.get_stored_rate(
            session,
            base_currency=payload.from_currency,
            quote_currency=payload.to_currency,
            rate_date=payload.as_of_date,
            require_exact_date=False,
        )
        rate_used = stored.rate
    return ConvertAmountResponse(
        original_amount=payload.amount,
        original_currency=payload.from_currency,
        converted_amount=money.amount,
        reporting_currency=payload.to_currency,
        as_of_date=payload.as_of_date,
        rate_used=rate_used,
    )


@router.post(
    "/fetch",
    response_model=ExchangeRateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def fetch_exchange_rate(
    payload: ExchangeRateFetchRequest,
    session: SessionDep,
    request: Request,
    _current_user: CurrentUserDep,
) -> ExchangeRateResponse:
    provider = get_exchange_rate_provider(request.app)
    return await exchange_rate_service.fetch_and_store_rate(
        session,
        provider=provider,
        base_currency=payload.base_currency,
        quote_currency=payload.quote_currency,
        rate_date=payload.rate_date,
        overwrite_existing=payload.overwrite_existing,
    )
