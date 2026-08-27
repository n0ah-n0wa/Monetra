"""User profile update schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.domain.currency import normalize_currency


class UserUpdateRequest(BaseModel):
    reporting_currency: str = Field(min_length=3, max_length=3)

    @field_validator("reporting_currency")
    @classmethod
    def validate_reporting_currency(cls, value: str) -> str:
        return normalize_currency(value)
