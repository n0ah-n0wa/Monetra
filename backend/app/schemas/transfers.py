"""Transfer API schemas."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.transactions import validate_positive_amount


class TransferCreateRequest(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    source_amount: Decimal = Field(max_digits=19, decimal_places=4)
    destination_amount: Decimal | None = Field(
        default=None,
        max_digits=19,
        decimal_places=4,
    )
    exchange_rate: Decimal | None = Field(
        default=None,
        max_digits=19,
        decimal_places=8,
    )
    transaction_date: date
    description: str | None = Field(default=None, max_length=500)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("source_amount")
    @classmethod
    def validate_source_amount(cls, value: Decimal) -> Decimal:
        return validate_positive_amount(value)

    @field_validator("destination_amount")
    @classmethod
    def validate_destination_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_positive_amount(value)


class TransferResponse(BaseModel):
    id: str
    source_account_id: str
    destination_account_id: str
    source_amount: Decimal
    source_currency: str
    destination_amount: Decimal
    destination_currency: str
    exchange_rate: Decimal | None
    transaction_date: date
    description: str | None
    idempotency_key: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
