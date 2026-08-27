"""Analytics endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.domain.analytics_periods import AnalyticsPeriodPreset
from app.schemas.analytics import (
    BalanceOverTimeResponse,
    BudgetUtilizationAnalyticsResponse,
    IncomeVsExpensesResponse,
    LargestTransactionsResponse,
    NetCashFlowResponse,
    PeriodComparisonResponse,
    SavingsRateResponse,
    SpendingByCategoryResponse,
    SpendingTrendsResponse,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])

PeriodQuery = Annotated[AnalyticsPeriodPreset, Query()]
DEFAULT_LAST_30 = AnalyticsPeriodPreset.LAST_30_DAYS
DEFAULT_CURRENT_MONTH = AnalyticsPeriodPreset.CURRENT_MONTH


@router.get("/income-vs-expenses", response_model=IncomeVsExpensesResponse)
async def get_income_vs_expenses(
    session: SessionDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_LAST_30,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> IncomeVsExpensesResponse:
    return await analytics_service.get_income_vs_expenses(
        session,
        user=current_user,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )


@router.get("/net-cash-flow", response_model=NetCashFlowResponse)
async def get_net_cash_flow(
    session: SessionDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_LAST_30,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> NetCashFlowResponse:
    return await analytics_service.get_net_cash_flow(
        session,
        user=current_user,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )


@router.get("/balance-over-time", response_model=BalanceOverTimeResponse)
async def get_balance_over_time(
    session: SessionDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_LAST_30,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> BalanceOverTimeResponse:
    return await analytics_service.get_balance_over_time(
        session,
        user=current_user,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )


@router.get("/spending-by-category", response_model=SpendingByCategoryResponse)
async def get_spending_by_category(
    session: SessionDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_LAST_30,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> SpendingByCategoryResponse:
    return await analytics_service.get_spending_by_category(
        session,
        user=current_user,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )


@router.get("/spending-trends", response_model=SpendingTrendsResponse)
async def get_spending_trends(
    session: SessionDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_LAST_30,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> SpendingTrendsResponse:
    return await analytics_service.get_spending_trends(
        session,
        user=current_user,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )


@router.get("/savings-rate", response_model=SavingsRateResponse)
async def get_savings_rate(
    session: SessionDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_LAST_30,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> SavingsRateResponse:
    return await analytics_service.get_savings_rate(
        session,
        user=current_user,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )


@router.get("/period-comparison", response_model=PeriodComparisonResponse)
async def get_period_comparison(
    session: SessionDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_CURRENT_MONTH,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> PeriodComparisonResponse:
    return await analytics_service.get_period_comparison(
        session,
        user=current_user,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )


@router.get("/largest-expenses", response_model=LargestTransactionsResponse)
async def get_largest_expenses(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_LAST_30,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
    limit: Annotated[int, Query(ge=1)] = 10,
) -> LargestTransactionsResponse:
    return await analytics_service.get_largest_expenses(
        session,
        user=current_user,
        settings=settings,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
        limit=limit,
    )


@router.get("/largest-income", response_model=LargestTransactionsResponse)
async def get_largest_income(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_LAST_30,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
    limit: Annotated[int, Query(ge=1)] = 10,
) -> LargestTransactionsResponse:
    return await analytics_service.get_largest_income(
        session,
        user=current_user,
        settings=settings,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
        limit=limit,
    )


@router.get("/budget-utilization", response_model=BudgetUtilizationAnalyticsResponse)
async def get_budget_utilization_analytics(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    period: PeriodQuery = DEFAULT_CURRENT_MONTH,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> BudgetUtilizationAnalyticsResponse:
    return await analytics_service.get_budget_utilization_analytics(
        session,
        user=current_user,
        settings=settings,
        preset=period,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
    )
