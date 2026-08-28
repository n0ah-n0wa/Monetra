import { apiClient } from "@/api/client";
import type { BudgetUtilizationStatus } from "@/features/budgets/api";
import { toSearchParams } from "@/types/pagination";

export const ANALYTICS_PERIODS = [
  "last_7_days",
  "last_30_days",
  "last_90_days",
  "current_month",
  "previous_month",
  "current_year",
  "previous_year",
  "custom",
] as const;

export type AnalyticsPeriod = (typeof ANALYTICS_PERIODS)[number];

export type AnalyticsQueryParams = {
  period?: AnalyticsPeriod;
  as_of_date?: string;
  date_from?: string;
  date_to?: string;
  reporting_currency?: string;
  limit?: number;
};

export type AnalyticsPeriodResponse = {
  preset: AnalyticsPeriod;
  start_date: string;
  end_date: string;
  as_of_date: string;
};

export type IncomeVsExpensesResponse = {
  period: AnalyticsPeriodResponse;
  reporting_currency: string;
  income: string;
  expenses: string;
};

export type NetCashFlowResponse = {
  period: AnalyticsPeriodResponse;
  reporting_currency: string;
  granularity: string;
  total_net_cash_flow: string;
  points: Array<{
    bucket_date: string;
    income: string;
    expenses: string;
    net_cash_flow: string;
  }>;
};

export type BalanceOverTimeResponse = {
  period: AnalyticsPeriodResponse;
  reporting_currency: string;
  opening_balance: string;
  closing_balance: string;
  points: Array<{
    bucket_date: string;
    balance: string;
  }>;
};

export type SpendingByCategoryResponse = {
  period: AnalyticsPeriodResponse;
  reporting_currency: string;
  total_expenses: string;
  items: Array<{
    category_id: string;
    category_name: string;
    amount: string;
    percentage: string;
  }>;
};

export type SpendingTrendsResponse = {
  period: AnalyticsPeriodResponse;
  reporting_currency: string;
  granularity: string;
  total_expenses: string;
  points: Array<{
    bucket_date: string;
    amount: string;
  }>;
};

export type SavingsRateResponse = {
  period: AnalyticsPeriodResponse;
  reporting_currency: string;
  income: string;
  expenses: string;
  net_cash_flow: string;
  savings_rate_percent: string | null;
};

export type PeriodMetricComparison = {
  current: string;
  previous: string;
  change: string;
  change_percent: string | null;
};

export type PeriodComparisonResponse = {
  current_period: AnalyticsPeriodResponse;
  previous_period: AnalyticsPeriodResponse;
  reporting_currency: string;
  income: PeriodMetricComparison;
  expenses: PeriodMetricComparison;
  net_cash_flow: PeriodMetricComparison;
  savings_rate_percent: PeriodMetricComparison | null;
};

export type TopTransactionItem = {
  transaction_id: string;
  description: string;
  amount: string;
  currency: string;
  reporting_amount: string;
  transaction_date: string;
  category_name: string;
  account_name: string;
};

export type LargestTransactionsResponse = {
  period: AnalyticsPeriodResponse;
  reporting_currency: string;
  items: TopTransactionItem[];
};

export type BudgetUtilization = {
  as_of_date: string;
  period_start: string;
  period_end: string;
  budget_amount: string;
  spent_amount: string;
  remaining_amount: string;
  percentage_used: string;
  status: BudgetUtilizationStatus;
};

export type BudgetUtilizationAnalyticsItem = {
  budget: {
    id: string;
    name: string;
    amount: string;
    currency: string;
    period: string;
    scope: string;
    start_date: string;
    end_date: string | null;
    warning_threshold_percent: number;
    categories: Array<{ id: string; name: string }>;
    archived_at: string | null;
    created_at: string;
    updated_at: string;
    utilization: BudgetUtilization | null;
  };
  utilization: BudgetUtilization;
};

export type BudgetUtilizationAnalyticsResponse = {
  period: AnalyticsPeriodResponse;
  as_of_date: string;
  items: BudgetUtilizationAnalyticsItem[];
};

function analyticsPath(endpoint: string, params: AnalyticsQueryParams = {}): string {
  return `/analytics/${endpoint}${toSearchParams(params)}`;
}

export async function fetchIncomeVsExpenses(
  params: AnalyticsQueryParams = {},
): Promise<IncomeVsExpensesResponse> {
  return apiClient.get<IncomeVsExpensesResponse>(
    analyticsPath("income-vs-expenses", params),
  );
}

export async function fetchNetCashFlow(
  params: AnalyticsQueryParams = {},
): Promise<NetCashFlowResponse> {
  return apiClient.get<NetCashFlowResponse>(analyticsPath("net-cash-flow", params));
}

export async function fetchBalanceOverTime(
  params: AnalyticsQueryParams = {},
): Promise<BalanceOverTimeResponse> {
  return apiClient.get<BalanceOverTimeResponse>(
    analyticsPath("balance-over-time", params),
  );
}

export async function fetchSpendingByCategory(
  params: AnalyticsQueryParams = {},
): Promise<SpendingByCategoryResponse> {
  return apiClient.get<SpendingByCategoryResponse>(
    analyticsPath("spending-by-category", params),
  );
}

export async function fetchSpendingTrends(
  params: AnalyticsQueryParams = {},
): Promise<SpendingTrendsResponse> {
  return apiClient.get<SpendingTrendsResponse>(
    analyticsPath("spending-trends", params),
  );
}

export async function fetchSavingsRate(
  params: AnalyticsQueryParams = {},
): Promise<SavingsRateResponse> {
  return apiClient.get<SavingsRateResponse>(analyticsPath("savings-rate", params));
}

export async function fetchPeriodComparison(
  params: AnalyticsQueryParams = {},
): Promise<PeriodComparisonResponse> {
  return apiClient.get<PeriodComparisonResponse>(
    analyticsPath("period-comparison", params),
  );
}

export async function fetchLargestExpenses(
  params: AnalyticsQueryParams = {},
): Promise<LargestTransactionsResponse> {
  return apiClient.get<LargestTransactionsResponse>(
    analyticsPath("largest-expenses", params),
  );
}

export async function fetchLargestIncome(
  params: AnalyticsQueryParams = {},
): Promise<LargestTransactionsResponse> {
  return apiClient.get<LargestTransactionsResponse>(
    analyticsPath("largest-income", params),
  );
}

export async function fetchBudgetUtilizationAnalytics(
  params: AnalyticsQueryParams = {},
): Promise<BudgetUtilizationAnalyticsResponse> {
  return apiClient.get<BudgetUtilizationAnalyticsResponse>(
    analyticsPath("budget-utilization", params),
  );
}
