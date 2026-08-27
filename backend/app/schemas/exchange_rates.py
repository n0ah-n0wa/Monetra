"""Exchange rate API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.currency import normalize_currency
from app.domain.transfers import validate_exchange_rate


class ExchangeRateCreateRequest(BaseModel):
    base_currency: str = Field(min_length=3, max_length=3)
    quote_currency: str = Field(min_length=3, max_length=3)
    rate: Decimal = Field(max_digits=19, decimal_places=8)
    rate_date: date
    source: str | None = Field(default="manual", max_length=64)
    overwrite_existing: bool = False

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)

    @field_validator("rate")
    @classmethod
    def validate_rate(cls, value: Decimal) -> Decimal:
        return validate_exchange_rate(value)


class ExchangeRateFetchRequest(BaseModel):
    base_currency: str = Field(min_length=3, max_length=3)
    quote_currency: str = Field(min_length=3, max_length=3)
    rate_date: date | None = None
    overwrite_existing: bool = False

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)


class ConvertAmountRequest(BaseModel):
    amount: Decimal = Field(max_digits=19, decimal_places=4)
    from_currency: str = Field(min_length=3, max_length=3)
    to_currency: str = Field(min_length=3, max_length=3)
    as_of_date: date

    @field_validator("from_currency", "to_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)


class ExchangeRateResponse(BaseModel):
    id: str
    base_currency: str
    quote_currency: str
    rate: Decimal
    rate_date: date
    source: str | None
    retrieved_at: datetime
    created_at: datetime
    updated_at: datetime


class ConvertAmountResponse(BaseModel):
    original_amount: Decimal
    original_currency: str
    converted_amount: Decimal
    reporting_currency: str
    as_of_date: date
    rate_used: Decimal | None
