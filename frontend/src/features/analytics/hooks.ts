import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  fetchBalanceOverTime,
  fetchBudgetUtilizationAnalytics,
  fetchIncomeVsExpenses,
  fetchLargestExpenses,
  fetchNetCashFlow,
  fetchPeriodComparison,
  fetchSavingsRate,
  fetchSpendingByCategory,
  type AnalyticsQueryParams,
} from "@/features/analytics/api";
import { queryKeys } from "@/lib/query-client";

const DASHBOARD_PERIOD: AnalyticsQueryParams = { period: "current_month" };

type QueryOptions = {
  enabled?: boolean;
};

export function useIncomeVsExpensesQuery(
  params: AnalyticsQueryParams = DASHBOARD_PERIOD,
  options: QueryOptions = {},
) {
  return useQuery({
    queryKey: queryKeys.analytics.incomeVsExpenses(params),
    queryFn: () => fetchIncomeVsExpenses(params),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

export function useNetCashFlowQuery(
  params: AnalyticsQueryParams = DASHBOARD_PERIOD,
  options: QueryOptions = {},
) {
  return useQuery({
    queryKey: queryKeys.analytics.netCashFlow(params),
    queryFn: () => fetchNetCashFlow(params),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

export function useBalanceOverTimeQuery(
  params: AnalyticsQueryParams = DASHBOARD_PERIOD,
  options: QueryOptions = {},
) {
  return useQuery({
    queryKey: queryKeys.analytics.balanceOverTime(params),
    queryFn: () => fetchBalanceOverTime(params),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

export function useSavingsRateQuery(
  params: AnalyticsQueryParams = DASHBOARD_PERIOD,
  options: QueryOptions = {},
) {
  return useQuery({
    queryKey: queryKeys.analytics.savingsRate(params),
    queryFn: () => fetchSavingsRate(params),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

export function useSpendingByCategoryQuery(
  params: AnalyticsQueryParams = DASHBOARD_PERIOD,
  options: QueryOptions = {},
) {
  return useQuery({
    queryKey: queryKeys.analytics.spendingByCategory(params),
    queryFn: () => fetchSpendingByCategory(params),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

export function usePeriodComparisonQuery(
  params: AnalyticsQueryParams = DASHBOARD_PERIOD,
  options: QueryOptions = {},
) {
  return useQuery({
    queryKey: queryKeys.analytics.periodComparison(params),
    queryFn: () => fetchPeriodComparison(params),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

export function useLargestExpensesQuery(
  params: AnalyticsQueryParams = DASHBOARD_PERIOD,
  options: QueryOptions = {},
) {
  return useQuery({
    queryKey: queryKeys.analytics.largestExpenses(params),
    queryFn: () => fetchLargestExpenses({ ...params, limit: params.limit ?? 1 }),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

export function useBudgetUtilizationAnalyticsQuery(
  params: AnalyticsQueryParams = DASHBOARD_PERIOD,
  options: QueryOptions = {},
) {
  return useQuery({
    queryKey: queryKeys.analytics.budgetUtilization(params),
    queryFn: () => fetchBudgetUtilizationAnalytics(params),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}
