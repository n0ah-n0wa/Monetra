import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalyticsQueryParams } from "@/features/analytics/api";
import { AccessibleDataTable } from "@/features/analytics/components/AccessibleDataTable";
import { AnalyticsChartPanel } from "@/features/analytics/components/AnalyticsChartPanel";
import {
  chartScaleValue,
  formatChartMoneyTooltip,
} from "@/features/analytics/chart-display";
import { useIncomeVsExpensesQuery } from "@/features/analytics/hooks";
import { formatMoneyDisplay } from "@/lib/money";

type PanelProps = {
  params: AnalyticsQueryParams;
  enabled?: boolean;
};

export function IncomeVsExpensesPanel({ params, enabled = true }: PanelProps) {
  const query = useIncomeVsExpensesQuery(params, { enabled });
  const currency = query.data?.reporting_currency ?? params.reporting_currency ?? "USD";

  const chartData =
    query.data === undefined
      ? []
      : [
          {
            label: "Income",
            amount: query.data.income,
            scale: chartScaleValue(query.data.income),
          },
          {
            label: "Expenses",
            amount: query.data.expenses,
            scale: chartScaleValue(query.data.expenses),
          },
        ];

  return (
    <AnalyticsChartPanel
      title="Income vs expenses"
      description="Totals for the selected period from server analytics."
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={false}
      table={
        query.data ? (
          <AccessibleDataTable
            caption="Income and expenses for the selected period"
            columns={[
              { key: "metric", header: "Metric", cell: (row) => row.metric },
              {
                key: "amount",
                header: "Amount",
                align: "right",
                cell: (row) => row.amount,
              },
            ]}
            rows={[
              {
                id: "income",
                metric: "Income",
                amount: formatMoneyDisplay(query.data.income, currency),
              },
              {
                id: "expenses",
                metric: "Expenses",
                amount: formatMoneyDisplay(query.data.expenses, currency),
              },
            ]}
            getRowKey={(row) => row.id}
          />
        ) : null
      }
    >
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={48} />
          <Tooltip
            formatter={(_value, _name, item) =>
              formatChartMoneyTooltip(String(item.payload.amount), currency)
            }
          />
          <Legend />
          <Bar
            dataKey="scale"
            name="Amount"
            fill="var(--brand)"
            radius={[6, 6, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </AnalyticsChartPanel>
  );
}
