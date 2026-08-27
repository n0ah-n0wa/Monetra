"""Recurring transaction API schemas."""

from datetime import date
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.recurring import validate_date_range
from app.domain.transactions import validate_positive_amount
from app.models.enums import RecurringFrequency, TransactionType


class RecurringTransactionCreateRequest(BaseModel):
    account_id: UUID
    category_id: UUID
    transaction_type: TransactionType
    amount: Decimal = Field(max_digits=19, decimal_places=4)
    description: str = Field(min_length=1, max_length=500)
    frequency: RecurringFrequency
    start_date: date
    end_date: date | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        return validate_positive_amount(value)

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        validate_date_range(start_date=self.start_date, end_date=self.end_date)
        return self


class RecurringTransactionUpdateRequest(BaseModel):
    account_id: UUID | None = None
    category_id: UUID | None = None
    transaction_type: TransactionType | None = None
    amount: Decimal | None = Field(default=None, max_digits=19, decimal_places=4)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    frequency: RecurringFrequency | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_positive_amount(value)


class RecurringTransactionResponse(BaseModel):
    id: str
    account_id: str
    category_id: str
    transaction_type: TransactionType
    amount: Decimal
    currency: str
    description: str
    frequency: RecurringFrequency
    start_date: date
    end_date: date | None
    next_execution_date: date
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class RecurringExecutionResult(BaseModel):
    recurring_transaction_id: str
    execution_date: date
    transaction_id: str
    created: bool


class ProcessDueRecurringRequest(BaseModel):
    as_of_date: date | None = None


class ProcessDueRecurringResponse(BaseModel):
    as_of_date: date
    executions: list[RecurringExecutionResult]
