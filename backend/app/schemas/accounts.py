"""Financial account API schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.currency import normalize_currency
from app.models.enums import AccountStatus, AccountType


class AccountCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    account_type: AccountType
    currency: str = Field(min_length=3, max_length=3)
    opening_balance: Decimal = Field(
        default=Decimal("0"),
        max_digits=19,
        decimal_places=4,
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)


class AccountUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    account_type: AccountType | None = None


class AccountResponse(BaseModel):
    id: str
    name: str
    account_type: AccountType
    currency: str
    opening_balance: Decimal
    current_balance: Decimal
    status: AccountStatus
    archived_at: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
