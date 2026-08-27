import { apiClient } from "@/api/client";
import { toSearchParams } from "@/types/pagination";

export type IncomeVsExpenses = {
  period: { start_date: string; end_date: string };
  income_total: string;
  expense_total: string;
  net_total: string;
  currency: string;
};

export type AnalyticsParams = {
  start_date?: string;
  end_date?: string;
};

export async function fetchIncomeVsExpenses(
  params: AnalyticsParams = {},
): Promise<IncomeVsExpenses> {
  return apiClient.get<IncomeVsExpenses>(
    `/analytics/income-vs-expenses${toSearchParams(params)}`,
  );
}

export async function fetchNetCashFlow(params: AnalyticsParams = {}): Promise<{
  period: { start_date: string; end_date: string };
  net_cash_flow: string;
  currency: string;
}> {
  return apiClient.get(`/analytics/net-cash-flow${toSearchParams(params)}`);
}
