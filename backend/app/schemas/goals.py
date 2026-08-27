"""Financial goal API schemas."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.currency import normalize_currency
from app.domain.transactions import normalize_money, validate_positive_amount
from app.models.enums import GoalStatus


def validate_non_negative_amount(amount: Decimal) -> Decimal:
    normalized = normalize_money(amount)
    if normalized < Decimal("0"):
        raise ValueError("Amount must be greater than or equal to zero.")
    return normalized


class GoalCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(max_digits=19, decimal_places=4)
    current_amount: Decimal = Field(
        default=Decimal("0"),
        max_digits=19,
        decimal_places=4,
    )
    currency: str = Field(min_length=3, max_length=3)
    target_date: date | None = None
    linked_account_id: UUID | None = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)

    @field_validator("target_amount")
    @classmethod
    def validate_target_amount(cls, value: Decimal) -> Decimal:
        return validate_positive_amount(value)

    @field_validator("current_amount")
    @classmethod
    def validate_current_amount(cls, value: Decimal) -> Decimal:
        return validate_non_negative_amount(value)


class GoalUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Decimal | None = Field(default=None, max_digits=19, decimal_places=4)
    current_amount: Decimal | None = Field(
        default=None, max_digits=19, decimal_places=4
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    target_date: date | None = None
    linked_account_id: UUID | None = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_currency(value)

    @field_validator("target_amount")
    @classmethod
    def validate_target_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_positive_amount(value)

    @field_validator("current_amount")
    @classmethod
    def validate_current_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_non_negative_amount(value)


class GoalProgressResponse(BaseModel):
    as_of_date: date
    remaining_amount: Decimal
    completion_percentage: Decimal
    required_average_contribution: Decimal | None
    average_contribution_rate: Decimal | None
    projected_completion_date: date | None
    target_date_achievable: bool | None


class GoalResponse(BaseModel):
    id: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    target_date: date | None
    linked_account_id: str | None
    status: GoalStatus
    archived_at: str | None
    created_at: str
    updated_at: str
    progress: GoalProgressResponse | None = None

    model_config = {"from_attributes": True}
