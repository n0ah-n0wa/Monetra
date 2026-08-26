"""Transaction API schemas."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.transactions import validate_positive_amount
from app.models.enums import TransactionType


class TransactionSortField(StrEnum):
    TRANSACTION_DATE = "transaction_date"
    AMOUNT = "amount"
    CREATED_AT = "created_at"
    DESCRIPTION = "description"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class TransactionCreateRequest(BaseModel):
    account_id: UUID
    category_id: UUID
    transaction_type: TransactionType
    amount: Decimal = Field(max_digits=19, decimal_places=4)
    description: str = Field(min_length=1, max_length=500)
    transaction_date: date
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        return validate_positive_amount(value)


class TransactionUpdateRequest(BaseModel):
    account_id: UUID | None = None
    category_id: UUID | None = None
    transaction_type: TransactionType | None = None
    amount: Decimal | None = Field(default=None, max_digits=19, decimal_places=4)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    transaction_date: date | None = None
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_positive_amount(value)


class TransactionResponse(BaseModel):
    id: str
    account_id: str
    category_id: str
    transaction_type: TransactionType
    amount: Decimal
    currency: str
    description: str
    transaction_date: date
    notes: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
