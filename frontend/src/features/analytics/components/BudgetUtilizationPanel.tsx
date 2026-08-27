import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/Badge";
import type { AnalyticsQueryParams } from "@/features/analytics/api";
import { AccessibleDataTable } from "@/features/analytics/components/AccessibleDataTable";
import { AnalyticsChartPanel } from "@/features/analytics/components/AnalyticsChartPanel";
import {
  chartScaleValue,
  formatChartMoneyTooltip,
  formatChartPercentTooltip,
} from "@/features/analytics/chart-display";
import { useBudgetUtilizationAnalyticsQuery } from "@/features/analytics/hooks";
import { budgetStatusVariant } from "@/features/budgets/api";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";

type PanelProps = {
  params: AnalyticsQueryParams;
  enabled?: boolean;
};

export function BudgetUtilizationPanel({ params, enabled = true }: PanelProps) {
  const query = useBudgetUtilizationAnalyticsQuery(params, { enabled });

  const chartData =
    query.data?.items.map((item) => ({
      name: item.budget.name,
      percentage_used: item.utilization.percentage_used,
      scale: chartScaleValue(item.utilization.percentage_used),
      spent: item.utilization.spent_amount,
      budget: item.utilization.budget_amount,
      currency: item.budget.currency,
      status: item.utilization.status,
    })) ?? [];

  return (
    <AnalyticsChartPanel
      title="Budget utilization"
      description="Spending against configured budgets for the selected period."
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={query.isSuccess && chartData.length === 0}
      emptyTitle="No budgets to analyze"
      emptyDescription="Create budgets to track utilization here."
      table={
        query.data ? (
          <AccessibleDataTable
            caption="Budget utilization for the selected period"
            columns={[
              { key: "name", header: "Budget", cell: (row) => row.budget.name },
              {
                key: "spent",
                header: "Spent",
                align: "right",
                cell: (row) =>
                  formatMoneyDisplay(row.utilization.spent_amount, row.budget.currency),
              },
              {
                key: "budget",
                header: "Budget",
                align: "right",
                cell: (row) =>
                  formatMoneyDisplay(
                    row.utilization.budget_amount,
                    row.budget.currency,
                  ),
              },
              {
                key: "used",
                header: "Used",
                align: "right",
                cell: (row) => formatPercentDisplay(row.utilization.percentage_used),
              },
              {
                key: "status",
                header: "Status",
                cell: (row) => (
                  <Badge variant={budgetStatusVariant(row.utilization.status)}>
                    {row.utilization.status}
                  </Badge>
                ),
              },
            ]}
            rows={query.data.items}
            getRowKey={(row) => row.budget.id}
          />
        ) : null
      }
    >
      <ResponsiveContainer width="100%" height={280}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 8, right: 8, left: 8, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
          <YAxis type="category" dataKey="name" width={88} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(_value, _name, item) => {
              const row = item.payload as (typeof chartData)[number];
              return `${formatChartPercentTooltip(row.percentage_used)} · ${formatChartMoneyTooltip(row.spent, row.currency)} of ${formatChartMoneyTooltip(row.budget, row.currency)}`;
            }}
          />
          <Bar dataKey="scale" name="Used" fill="var(--brand)" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </AnalyticsChartPanel>
  );
}
