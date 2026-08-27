"""Budget API schemas."""

from datetime import date
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.budgets import validate_budget_date_range
from app.domain.currency import normalize_currency
from app.domain.transactions import validate_positive_amount
from app.models.enums import BudgetPeriod, BudgetScope, BudgetStatus


class BudgetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(max_digits=19, decimal_places=4)
    currency: str = Field(min_length=3, max_length=3)
    period: BudgetPeriod
    scope: BudgetScope
    start_date: date
    end_date: date | None = None
    warning_threshold_percent: int = Field(default=80, ge=0, le=100)
    category_ids: list[UUID] = Field(default_factory=list)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        return validate_positive_amount(value)

    @model_validator(mode="after")
    def validate_scope_and_dates(self) -> Self:
        validate_budget_date_range(start_date=self.start_date, end_date=self.end_date)
        if self.period == BudgetPeriod.CUSTOM and self.end_date is None:
            raise ValueError("Custom budgets require an end_date.")
        if self.scope == BudgetScope.CATEGORY and not self.category_ids:
            raise ValueError("Category budgets require at least one category_id.")
        if self.scope == BudgetScope.OVERALL and self.category_ids:
            raise ValueError("Overall budgets cannot include category_ids.")
        return self


class BudgetUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    amount: Decimal | None = Field(default=None, max_digits=19, decimal_places=4)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    period: BudgetPeriod | None = None
    scope: BudgetScope | None = None
    start_date: date | None = None
    end_date: date | None = None
    warning_threshold_percent: int | None = Field(default=None, ge=0, le=100)
    category_ids: list[UUID] | None = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_currency(value)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_positive_amount(value)


class BudgetCategorySummary(BaseModel):
    id: str
    name: str


class BudgetUtilizationResponse(BaseModel):
    as_of_date: date
    period_start: date
    period_end: date
    budget_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: Decimal
    status: BudgetStatus


class BudgetResponse(BaseModel):
    id: str
    name: str
    amount: Decimal
    currency: str
    period: BudgetPeriod
    scope: BudgetScope
    start_date: date
    end_date: date | None
    warning_threshold_percent: int
    categories: list[BudgetCategorySummary]
    archived_at: str | None
    created_at: str
    updated_at: str
    utilization: BudgetUtilizationResponse | None = None

    model_config = {"from_attributes": True}


class BudgetAnalyticsItem(BaseModel):
    budget: BudgetResponse
    utilization: BudgetUtilizationResponse


class BudgetAnalyticsResponse(BaseModel):
    as_of_date: date
    items: list[BudgetAnalyticsItem]
