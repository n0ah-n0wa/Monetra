import type { AnalyticsPeriod, AnalyticsQueryParams } from "@/features/analytics/api";

export type AnalyticsFilterState = {
  period: AnalyticsPeriod;
  date_from: string;
  date_to: string;
  reporting_currency: string;
};

export const ANALYTICS_PERIOD_LABELS: Record<AnalyticsPeriod, string> = {
  last_7_days: "Last 7 days",
  last_30_days: "Last 30 days",
  last_90_days: "Last 90 days",
  current_month: "Current month",
  previous_month: "Previous month",
  current_year: "Current year",
  previous_year: "Previous year",
  custom: "Custom range",
};

export function defaultAnalyticsFilters(
  reportingCurrency = "USD",
): AnalyticsFilterState {
  return {
    period: "last_30_days",
    date_from: "",
    date_to: "",
    reporting_currency: reportingCurrency,
  };
}

export function filtersToAnalyticsParams(
  filters: AnalyticsFilterState,
): AnalyticsQueryParams {
  const currency = filters.reporting_currency.trim().toUpperCase();

  if (filters.period === "custom") {
    return {
      period: "custom",
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      reporting_currency: currency || undefined,
    };
  }

  return {
    period: filters.period,
    reporting_currency: currency || undefined,
  };
}

export function formatResolvedPeriod(
  startDate: string,
  endDate: string,
  currency: string,
): string {
  return `${startDate} to ${endDate} · ${currency}`;
}
