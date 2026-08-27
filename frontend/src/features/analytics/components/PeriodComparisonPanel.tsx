import { DashboardWidget } from "@/features/dashboard/components/DashboardWidget";
import type { AnalyticsQueryParams } from "@/features/analytics/api";
import { AccessibleDataTable } from "@/features/analytics/components/AccessibleDataTable";
import { usePeriodComparisonQuery } from "@/features/analytics/hooks";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";

type PanelProps = {
  params: AnalyticsQueryParams;
  enabled?: boolean;
};

function formatChangePercent(value: string | null): string {
  if (value === null) {
    return "—";
  }
  const trimmed = value.trim();
  if (trimmed.startsWith("-")) {
    return `↓ ${formatPercentDisplay(trimmed.slice(1))}`;
  }
  return `↑ ${formatPercentDisplay(trimmed)}`;
}

export function PeriodComparisonPanel({ params, enabled = true }: PanelProps) {
  const query = usePeriodComparisonQuery(params, { enabled });
  const currency = query.data?.reporting_currency ?? params.reporting_currency ?? "USD";

  const rows = query.data
    ? [
        {
          id: "income",
          metric: "Income",
          current: formatMoneyDisplay(query.data.income.current, currency),
          previous: formatMoneyDisplay(query.data.income.previous, currency),
          change: formatMoneyDisplay(query.data.income.change, currency),
          changePercent: formatChangePercent(query.data.income.change_percent),
        },
        {
          id: "expenses",
          metric: "Expenses",
          current: formatMoneyDisplay(query.data.expenses.current, currency),
          previous: formatMoneyDisplay(query.data.expenses.previous, currency),
          change: formatMoneyDisplay(query.data.expenses.change, currency),
          changePercent: formatChangePercent(query.data.expenses.change_percent),
        },
        {
          id: "net",
          metric: "Net cash flow",
          current: formatMoneyDisplay(query.data.net_cash_flow.current, currency),
          previous: formatMoneyDisplay(query.data.net_cash_flow.previous, currency),
          change: formatMoneyDisplay(query.data.net_cash_flow.change, currency),
          changePercent: formatChangePercent(query.data.net_cash_flow.change_percent),
        },
      ]
    : [];

  return (
    <DashboardWidget
      title="Period comparison"
      description={
        query.data
          ? `${query.data.current_period.start_date} to ${query.data.current_period.end_date} compared with ${query.data.previous_period.start_date} to ${query.data.previous_period.end_date}.`
          : "Compare current and previous periods using server analytics."
      }
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={false}
      className="analytics-panel analytics-panel--full"
    >
      <AccessibleDataTable
        caption="Period-over-period comparison from server analytics"
        columns={[
          { key: "metric", header: "Metric", cell: (row) => row.metric },
          {
            key: "current",
            header: "Current",
            align: "right",
            cell: (row) => row.current,
          },
          {
            key: "previous",
            header: "Previous",
            align: "right",
            cell: (row) => row.previous,
          },
          {
            key: "change",
            header: "Change",
            align: "right",
            cell: (row) => row.change,
          },
          {
            key: "changePercent",
            header: "Change %",
            align: "right",
            cell: (row) => row.changePercent,
          },
        ]}
        rows={rows}
        getRowKey={(row) => row.id}
      />
      {query.data?.savings_rate_percent ? (
        <p className="analytics-comparison-note">
          Savings rate: {formatPercentDisplay(query.data.savings_rate_percent.current)}{" "}
          (previous {formatPercentDisplay(query.data.savings_rate_percent.previous)},
          change {formatChangePercent(query.data.savings_rate_percent.change_percent)})
        </p>
      ) : null}
    </DashboardWidget>
  );
}
