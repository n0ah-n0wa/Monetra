"""Analytics orchestration and reporting-currency conversion."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ValidationAppError
from app.domain.analytics import (
    compute_net_cash_flow,
    compute_period_change,
    compute_period_change_percent,
    compute_savings_rate,
)
from app.domain.analytics_periods import (
    AnalyticsPeriodPreset,
    bucket_date,
    iter_dates,
    resolve_analytics_period,
    resolve_comparison_period,
    trend_granularity,
)
from app.domain.currency import normalize_currency
from app.domain.transactions import normalize_money
from app.models.enums import TransactionType
from app.models.user import User
from app.repositories import analytics_repository as analytics_repo
from app.repositories import exchange_rate_repository as exchange_rate_repo
from app.schemas.analytics import (
    AnalyticsPeriodResponse,
    BalanceOverTimePoint,
    BalanceOverTimeResponse,
    BudgetUtilizationAnalyticsResponse,
    CategorySpendingItem,
    IncomeVsExpensesResponse,
    LargestTransactionsResponse,
    NetCashFlowPoint,
    NetCashFlowResponse,
    PeriodComparisonResponse,
    PeriodMetricComparison,
    SavingsRateResponse,
    SpendingByCategoryResponse,
    SpendingTrendPoint,
    SpendingTrendsResponse,
    TopTransactionItem,
)
from app.services import budget_service


@dataclass(frozen=True)
class ResolvedAnalyticsPeriod:
    preset: AnalyticsPeriodPreset
    as_of_date: date
    start_date: date
    end_date: date
    reporting_currency: str


def _resolve_period(
    *,
    user: User,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None,
    date_from: date | None,
    date_to: date | None,
    reporting_currency: str | None,
) -> ResolvedAnalyticsPeriod:
    effective_as_of = as_of_date or datetime.now(UTC).date()
    start_date, end_date = resolve_analytics_period(
        preset=preset,
        as_of_date=effective_as_of,
        date_from=date_from,
        date_to=date_to,
    )
    currency = normalize_currency(reporting_currency or user.reporting_currency)
    return ResolvedAnalyticsPeriod(
        preset=preset,
        as_of_date=effective_as_of,
        start_date=start_date,
        end_date=end_date,
        reporting_currency=currency,
    )


def _period_response(resolved: ResolvedAnalyticsPeriod) -> AnalyticsPeriodResponse:
    return AnalyticsPeriodResponse(
        preset=resolved.preset,
        start_date=resolved.start_date,
        end_date=resolved.end_date,
        as_of_date=resolved.as_of_date,
    )


# Bound candidate scans for top-N ranking after FX conversion.
_TOP_TRANSACTION_CANDIDATE_CAP = 10_000


async def _build_rate_lookup(
    session: AsyncSession,
    *,
    reporting_currency: str,
    pairs: set[tuple[str, date]],
) -> dict[tuple[str, date], Decimal]:
    lookup: dict[tuple[str, date], Decimal] = {}
    by_currency: dict[str, set[date]] = {}
    for currency, rate_date in pairs:
        if currency == reporting_currency:
            lookup[(currency, rate_date)] = Decimal("1")
            continue
        by_currency.setdefault(currency, set()).add(rate_date)
    for currency, dates in by_currency.items():
        rates = await exchange_rate_repo.get_rates_on_or_before_dates(
            session,
            base_currency=currency,
            quote_currency=reporting_currency,
            dates=dates,
        )
        missing = sorted(date_value for date_value in dates if date_value not in rates)
        if missing:
            raise ValidationAppError(
                code="MISSING_EXCHANGE_RATE",
                message=(
                    f"No exchange rate found for {currency}/{reporting_currency} "
                    f"on or before {missing[0].isoformat()}."
                ),
                details={
                    "base_currency": currency,
                    "quote_currency": reporting_currency,
                    "missing_dates": [value.isoformat() for value in missing],
                },
            )
        for rate_date in dates:
            lookup[(currency, rate_date)] = rates[rate_date]
    return lookup


def _convert_amount(
    *,
    amount: Decimal,
    currency: str,
    rate_date: date,
    reporting_currency: str,
    rate_lookup: dict[tuple[str, date], Decimal],
) -> Decimal:
    if currency == reporting_currency:
        return normalize_money(amount)
    rate = rate_lookup[(currency, rate_date)]
    return normalize_money(amount * rate)


async def _aggregate_income_expenses(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resolved: ResolvedAnalyticsPeriod,
) -> tuple[Decimal, Decimal]:
    rows = await analytics_repo.sum_income_expenses_by_currency_and_date(
        session,
        user_id=user_id,
        start_date=resolved.start_date,
        end_date=resolved.end_date,
    )
    pairs = {(row.currency, row.bucket_date) for row in rows}
    rate_lookup = await _build_rate_lookup(
        session,
        reporting_currency=resolved.reporting_currency,
        pairs=pairs,
    )
    income = Decimal("0")
    expenses = Decimal("0")
    for row in rows:
        converted = _convert_amount(
            amount=row.total,
            currency=row.currency,
            rate_date=row.bucket_date,
            reporting_currency=resolved.reporting_currency,
            rate_lookup=rate_lookup,
        )
        if row.transaction_type == TransactionType.INCOME:
            income = normalize_money(income + converted)
        else:
            expenses = normalize_money(expenses + converted)
    return income, expenses


async def get_income_vs_expenses(
    session: AsyncSession,
    *,
    user: User,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> IncomeVsExpensesResponse:
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )
    income, expenses = await _aggregate_income_expenses(
        session,
        user_id=user.id,
        resolved=resolved,
    )
    return IncomeVsExpensesResponse(
        period=_period_response(resolved),
        reporting_currency=resolved.reporting_currency,
        income=normalize_money(income),
        expenses=normalize_money(expenses),
    )


async def get_net_cash_flow(
    session: AsyncSession,
    *,
    user: User,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> NetCashFlowResponse:
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )
    rows = await analytics_repo.sum_income_expenses_by_currency_and_date(
        session,
        user_id=user.id,
        start_date=resolved.start_date,
        end_date=resolved.end_date,
    )
    granularity = trend_granularity(resolved.start_date, resolved.end_date)
    pairs = {(row.currency, row.bucket_date) for row in rows}
    rate_lookup = await _build_rate_lookup(
        session,
        reporting_currency=resolved.reporting_currency,
        pairs=pairs,
    )

    income_by_bucket: dict[date, Decimal] = {}
    expenses_by_bucket: dict[date, Decimal] = {}
    for row in rows:
        bucket = bucket_date(row.bucket_date, granularity)
        converted = _convert_amount(
            amount=row.total,
            currency=row.currency,
            rate_date=row.bucket_date,
            reporting_currency=resolved.reporting_currency,
            rate_lookup=rate_lookup,
        )
        if row.transaction_type == TransactionType.INCOME:
            income_by_bucket[bucket] = normalize_money(
                income_by_bucket.get(bucket, Decimal("0")) + converted,
            )
        else:
            expenses_by_bucket[bucket] = normalize_money(
                expenses_by_bucket.get(bucket, Decimal("0")) + converted,
            )

    bucket_keys = sorted(set(income_by_bucket) | set(expenses_by_bucket))
    points: list[NetCashFlowPoint] = []
    total_net = Decimal("0")
    for bucket in bucket_keys:
        income = income_by_bucket.get(bucket, Decimal("0"))
        expenses = expenses_by_bucket.get(bucket, Decimal("0"))
        net = compute_net_cash_flow(income=income, expenses=expenses)
        total_net = normalize_money(total_net + net)
        points.append(
            NetCashFlowPoint(
                bucket_date=bucket,
                income=income,
                expenses=expenses,
                net_cash_flow=net,
            ),
        )

    return NetCashFlowResponse(
        period=_period_response(resolved),
        reporting_currency=resolved.reporting_currency,
        granularity=granularity,
        total_net_cash_flow=total_net,
        points=points,
    )


async def _opening_balance_at_date(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    reporting_currency: str,
    on_date: date,
) -> Decimal:
    """Balance immediately before activity on ``on_date``, in reporting currency.

    Opening balances convert at the rate on/before ``on_date``. Historical
    ledger activity converts at each transaction date's rate.
    """
    opening_rows = await analytics_repo.sum_opening_balances_by_currency(
        session,
        user_id=user_id,
    )
    pre_period_rows = await analytics_repo.sum_ledger_deltas_before_date(
        session,
        user_id=user_id,
        before_date=on_date,
    )
    pairs = {
        (row.currency, on_date) for row in opening_rows if row.total != Decimal("0")
    }
    pairs.update(
        (row.currency, row.bucket_date)
        for row in pre_period_rows
        if row.total != Decimal("0")
    )
    rate_lookup = await _build_rate_lookup(
        session,
        reporting_currency=reporting_currency,
        pairs=pairs,
    )
    total = Decimal("0")
    for opening in opening_rows:
        if opening.total == Decimal("0"):
            continue
        total = normalize_money(
            total
            + _convert_amount(
                amount=opening.total,
                currency=opening.currency,
                rate_date=on_date,
                reporting_currency=reporting_currency,
                rate_lookup=rate_lookup,
            ),
        )
    for ledger in pre_period_rows:
        if ledger.total == Decimal("0"):
            continue
        total = normalize_money(
            total
            + _convert_amount(
                amount=ledger.total,
                currency=ledger.currency,
                rate_date=ledger.bucket_date,
                reporting_currency=reporting_currency,
                rate_lookup=rate_lookup,
            ),
        )
    return total


async def get_balance_over_time(
    session: AsyncSession,
    *,
    user: User,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> BalanceOverTimeResponse:
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )
    delta_rows = await analytics_repo.sum_ledger_deltas_by_day(
        session,
        user_id=user.id,
        start_date=resolved.start_date,
        end_date=resolved.end_date,
    )
    pairs = {(row.currency, row.bucket_date) for row in delta_rows}
    rate_lookup = await _build_rate_lookup(
        session,
        reporting_currency=resolved.reporting_currency,
        pairs=pairs,
    )

    daily_delta: dict[date, Decimal] = {}
    for row in delta_rows:
        converted = _convert_amount(
            amount=row.delta,
            currency=row.currency,
            rate_date=row.bucket_date,
            reporting_currency=resolved.reporting_currency,
            rate_lookup=rate_lookup,
        )
        daily_delta[row.bucket_date] = normalize_money(
            daily_delta.get(row.bucket_date, Decimal("0")) + converted,
        )

    running = await _opening_balance_at_date(
        session,
        user_id=user.id,
        reporting_currency=resolved.reporting_currency,
        on_date=resolved.start_date,
    )
    opening_balance = running
    points: list[BalanceOverTimePoint] = []
    for day in iter_dates(resolved.start_date, resolved.end_date):
        running = normalize_money(running + daily_delta.get(day, Decimal("0")))
        points.append(BalanceOverTimePoint(bucket_date=day, balance=running))

    return BalanceOverTimeResponse(
        period=_period_response(resolved),
        reporting_currency=resolved.reporting_currency,
        opening_balance=opening_balance,
        closing_balance=running,
        points=points,
    )


async def get_spending_by_category(
    session: AsyncSession,
    *,
    user: User,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> SpendingByCategoryResponse:
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )
    rows = await analytics_repo.sum_expenses_by_category_and_date(
        session,
        user_id=user.id,
        start_date=resolved.start_date,
        end_date=resolved.end_date,
    )
    pairs = {(row.currency, row.bucket_date) for row in rows}
    rate_lookup = await _build_rate_lookup(
        session,
        reporting_currency=resolved.reporting_currency,
        pairs=pairs,
    )

    totals_by_category: dict[uuid.UUID, tuple[str, Decimal]] = {}
    total_expenses = Decimal("0")
    for row in rows:
        converted = _convert_amount(
            amount=row.total,
            currency=row.currency,
            rate_date=row.bucket_date,
            reporting_currency=resolved.reporting_currency,
            rate_lookup=rate_lookup,
        )
        total_expenses = normalize_money(total_expenses + converted)
        if row.category_id in totals_by_category:
            name, existing = totals_by_category[row.category_id]
            totals_by_category[row.category_id] = (
                name,
                normalize_money(existing + converted),
            )
        else:
            totals_by_category[row.category_id] = (row.category_name, converted)

    items: list[CategorySpendingItem] = []
    for category_id, (name, amount) in sorted(
        totals_by_category.items(),
        key=lambda item: item[1][1],
        reverse=True,
    ):
        percentage = Decimal("0")
        if total_expenses > Decimal("0"):
            percentage = normalize_money((amount / total_expenses) * Decimal("100"))
        items.append(
            CategorySpendingItem(
                category_id=str(category_id),
                category_name=name,
                amount=amount,
                percentage=percentage,
            ),
        )

    return SpendingByCategoryResponse(
        period=_period_response(resolved),
        reporting_currency=resolved.reporting_currency,
        total_expenses=total_expenses,
        items=items,
    )


async def get_spending_trends(
    session: AsyncSession,
    *,
    user: User,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> SpendingTrendsResponse:
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )
    rows = await analytics_repo.sum_daily_expenses_by_currency(
        session,
        user_id=user.id,
        start_date=resolved.start_date,
        end_date=resolved.end_date,
    )
    granularity = trend_granularity(resolved.start_date, resolved.end_date)
    pairs = {(row.currency, row.bucket_date) for row in rows}
    rate_lookup = await _build_rate_lookup(
        session,
        reporting_currency=resolved.reporting_currency,
        pairs=pairs,
    )

    bucket_totals: dict[date, Decimal] = {}
    total_expenses = Decimal("0")
    for row in rows:
        bucket = bucket_date(row.bucket_date, granularity)
        converted = _convert_amount(
            amount=row.total,
            currency=row.currency,
            rate_date=row.bucket_date,
            reporting_currency=resolved.reporting_currency,
            rate_lookup=rate_lookup,
        )
        total_expenses = normalize_money(total_expenses + converted)
        bucket_totals[bucket] = normalize_money(
            bucket_totals.get(bucket, Decimal("0")) + converted,
        )

    points = [
        SpendingTrendPoint(bucket_date=bucket, amount=amount)
        for bucket, amount in sorted(bucket_totals.items())
    ]
    return SpendingTrendsResponse(
        period=_period_response(resolved),
        reporting_currency=resolved.reporting_currency,
        granularity=granularity,
        total_expenses=total_expenses,
        points=points,
    )


async def get_savings_rate(
    session: AsyncSession,
    *,
    user: User,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> SavingsRateResponse:
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )
    income, expenses = await _aggregate_income_expenses(
        session,
        user_id=user.id,
        resolved=resolved,
    )
    net = compute_net_cash_flow(income=income, expenses=expenses)
    return SavingsRateResponse(
        period=_period_response(resolved),
        reporting_currency=resolved.reporting_currency,
        income=income,
        expenses=expenses,
        net_cash_flow=net,
        savings_rate_percent=compute_savings_rate(income=income, expenses=expenses),
    )


def _metric_comparison(current: Decimal, previous: Decimal) -> PeriodMetricComparison:
    return PeriodMetricComparison(
        current=current,
        previous=previous,
        change=compute_period_change(current=current, previous=previous),
        change_percent=compute_period_change_percent(
            current=current, previous=previous
        ),
    )


async def get_period_comparison(
    session: AsyncSession,
    *,
    user: User,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
) -> PeriodComparisonResponse:
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )
    previous_start, previous_end = resolve_comparison_period(
        preset=resolved.preset,
        start_date=resolved.start_date,
        end_date=resolved.end_date,
        as_of_date=resolved.as_of_date,
    )
    current_income, current_expenses = await _aggregate_income_expenses(
        session,
        user_id=user.id,
        resolved=resolved,
    )
    previous_resolved = ResolvedAnalyticsPeriod(
        preset=resolved.preset,
        as_of_date=resolved.as_of_date,
        start_date=previous_start,
        end_date=previous_end,
        reporting_currency=resolved.reporting_currency,
    )
    previous_income, previous_expenses = await _aggregate_income_expenses(
        session,
        user_id=user.id,
        resolved=previous_resolved,
    )
    current_net = compute_net_cash_flow(
        income=current_income,
        expenses=current_expenses,
    )
    previous_net = compute_net_cash_flow(
        income=previous_income,
        expenses=previous_expenses,
    )
    current_savings = compute_savings_rate(
        income=current_income,
        expenses=current_expenses,
    )
    previous_savings = compute_savings_rate(
        income=previous_income,
        expenses=previous_expenses,
    )
    savings_comparison = None
    if current_savings is not None and previous_savings is not None:
        savings_comparison = PeriodMetricComparison(
            current=current_savings,
            previous=previous_savings,
            change=compute_period_change(
                current=current_savings,
                previous=previous_savings,
            ),
            change_percent=compute_period_change_percent(
                current=current_savings,
                previous=previous_savings,
            ),
        )

    return PeriodComparisonResponse(
        current_period=_period_response(resolved),
        previous_period=AnalyticsPeriodResponse(
            preset=resolved.preset,
            start_date=previous_start,
            end_date=previous_end,
            as_of_date=resolved.as_of_date,
        ),
        reporting_currency=resolved.reporting_currency,
        income=_metric_comparison(current_income, previous_income),
        expenses=_metric_comparison(current_expenses, previous_expenses),
        net_cash_flow=_metric_comparison(current_net, previous_net),
        savings_rate_percent=savings_comparison,
    )


async def _top_transactions_response(
    session: AsyncSession,
    *,
    user: User,
    resolved: ResolvedAnalyticsPeriod,
    transaction_type: TransactionType,
    limit: int,
) -> LargestTransactionsResponse:
    rows = await analytics_repo.list_transactions_for_ranking(
        session,
        user_id=user.id,
        transaction_type=transaction_type,
        start_date=resolved.start_date,
        end_date=resolved.end_date,
        max_candidates=_TOP_TRANSACTION_CANDIDATE_CAP,
    )
    pairs = {(row.currency, row.transaction_date) for row in rows}
    rate_lookup = await _build_rate_lookup(
        session,
        reporting_currency=resolved.reporting_currency,
        pairs=pairs,
    )
    ranked = [
        TopTransactionItem(
            transaction_id=str(row.transaction_id),
            description=row.description,
            amount=row.amount,
            currency=row.currency,
            reporting_amount=_convert_amount(
                amount=row.amount,
                currency=row.currency,
                rate_date=row.transaction_date,
                reporting_currency=resolved.reporting_currency,
                rate_lookup=rate_lookup,
            ),
            transaction_date=row.transaction_date,
            category_name=row.category_name,
            account_name=row.account_name,
        )
        for row in rows
    ]
    ranked.sort(
        key=lambda item: (item.reporting_amount, item.transaction_date),
        reverse=True,
    )
    return LargestTransactionsResponse(
        period=_period_response(resolved),
        reporting_currency=resolved.reporting_currency,
        items=ranked[:limit],
    )


async def get_largest_expenses(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
    limit: int = 10,
) -> LargestTransactionsResponse:
    if limit < 1 or limit > settings.api_max_page_size:
        raise ValidationAppError(
            code="INVALID_LIMIT",
            message=f"limit must be between 1 and {settings.api_max_page_size}.",
        )
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )
    return await _top_transactions_response(
        session,
        user=user,
        resolved=resolved,
        transaction_type=TransactionType.EXPENSE,
        limit=limit,
    )


async def get_largest_income(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reporting_currency: str | None = None,
    limit: int = 10,
) -> LargestTransactionsResponse:
    if limit < 1 or limit > settings.api_max_page_size:
        raise ValidationAppError(
            code="INVALID_LIMIT",
            message=f"limit must be between 1 and {settings.api_max_page_size}.",
        )
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=reporting_currency,
    )
    return await _top_transactions_response(
        session,
        user=user,
        resolved=resolved,
        transaction_type=TransactionType.INCOME,
        limit=limit,
    )


async def get_budget_utilization_analytics(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    preset: AnalyticsPeriodPreset,
    as_of_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> BudgetUtilizationAnalyticsResponse:
    resolved = _resolve_period(
        user=user,
        preset=preset,
        as_of_date=as_of_date,
        date_from=date_from,
        date_to=date_to,
        reporting_currency=None,
    )
    analytics = await budget_service.get_budget_analytics(
        session,
        user_id=user.id,
        settings=settings,
        as_of_date=resolved.end_date,
    )
    return BudgetUtilizationAnalyticsResponse(
        period=_period_response(resolved),
        as_of_date=analytics.as_of_date,
        items=analytics.items,
    )
