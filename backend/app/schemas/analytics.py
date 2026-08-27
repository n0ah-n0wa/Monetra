"""Analytics API schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.domain.analytics_periods import AnalyticsPeriodPreset
from app.schemas.budgets import BudgetAnalyticsItem


class AnalyticsPeriodResponse(BaseModel):
    preset: AnalyticsPeriodPreset
    start_date: date
    end_date: date
    as_of_date: date


class IncomeVsExpensesResponse(BaseModel):
    period: AnalyticsPeriodResponse
    reporting_currency: str
    income: Decimal
    expenses: Decimal


class NetCashFlowPoint(BaseModel):
    bucket_date: date
    income: Decimal
    expenses: Decimal
    net_cash_flow: Decimal


class NetCashFlowResponse(BaseModel):
    period: AnalyticsPeriodResponse
    reporting_currency: str
    granularity: str
    total_net_cash_flow: Decimal
    points: list[NetCashFlowPoint]


class BalanceOverTimePoint(BaseModel):
    bucket_date: date
    balance: Decimal


class BalanceOverTimeResponse(BaseModel):
    period: AnalyticsPeriodResponse
    reporting_currency: str
    opening_balance: Decimal
    closing_balance: Decimal
    points: list[BalanceOverTimePoint]


class CategorySpendingItem(BaseModel):
    category_id: str
    category_name: str
    amount: Decimal
    percentage: Decimal


class SpendingByCategoryResponse(BaseModel):
    period: AnalyticsPeriodResponse
    reporting_currency: str
    total_expenses: Decimal
    items: list[CategorySpendingItem]


class SpendingTrendPoint(BaseModel):
    bucket_date: date
    amount: Decimal


class SpendingTrendsResponse(BaseModel):
    period: AnalyticsPeriodResponse
    reporting_currency: str
    granularity: str
    total_expenses: Decimal
    points: list[SpendingTrendPoint]


class SavingsRateResponse(BaseModel):
    period: AnalyticsPeriodResponse
    reporting_currency: str
    income: Decimal
    expenses: Decimal
    net_cash_flow: Decimal
    savings_rate_percent: Decimal | None


class PeriodMetricComparison(BaseModel):
    current: Decimal
    previous: Decimal
    change: Decimal
    change_percent: Decimal | None


class PeriodComparisonResponse(BaseModel):
    current_period: AnalyticsPeriodResponse
    previous_period: AnalyticsPeriodResponse
    reporting_currency: str
    income: PeriodMetricComparison
    expenses: PeriodMetricComparison
    net_cash_flow: PeriodMetricComparison
    savings_rate_percent: PeriodMetricComparison | None = None


class TopTransactionItem(BaseModel):
    transaction_id: str
    description: str
    amount: Decimal
    currency: str
    reporting_amount: Decimal
    transaction_date: date
    category_name: str
    account_name: str


class LargestTransactionsResponse(BaseModel):
    period: AnalyticsPeriodResponse
    reporting_currency: str
    items: list[TopTransactionItem]


class BudgetUtilizationAnalyticsResponse(BaseModel):
    period: AnalyticsPeriodResponse
    as_of_date: date
    items: list[BudgetAnalyticsItem]
