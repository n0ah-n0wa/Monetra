import {
  Bar,
  BarChart,
  CartesianGrid,
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
  formatChartPercentTooltip,
} from "@/features/analytics/chart-display";
import { useSpendingByCategoryQuery } from "@/features/analytics/hooks";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";

type PanelProps = {
  params: AnalyticsQueryParams;
  enabled?: boolean;
};

export function SpendingByCategoryPanel({ params, enabled = true }: PanelProps) {
  const query = useSpendingByCategoryQuery(params, { enabled });
  const currency = query.data?.reporting_currency ?? params.reporting_currency ?? "USD";

  const chartData =
    query.data?.items.map((item) => ({
      category: item.category_name,
      amount: item.amount,
      percentage: item.percentage,
      scale: chartScaleValue(item.amount),
    })) ?? [];

  return (
    <AnalyticsChartPanel
      title="Spending by category"
      description="Expense distribution calculated on the server."
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={query.isSuccess && query.data.items.length === 0}
      emptyTitle="No spending in this period"
      emptyDescription="Expense transactions will appear here when recorded."
      table={
        query.data ? (
          <AccessibleDataTable
            caption="Spending by category for the selected period"
            columns={[
              { key: "category", header: "Category", cell: (row) => row.category_name },
              {
                key: "amount",
                header: "Amount",
                align: "right",
                cell: (row) => formatMoneyDisplay(row.amount, currency),
              },
              {
                key: "share",
                header: "Share",
                align: "right",
                cell: (row) => formatPercentDisplay(row.percentage),
              },
            ]}
            rows={query.data.items}
            getRowKey={(row) => row.category_id}
            footer={
              <tr>
                <th scope="row">Total expenses</th>
                <td colSpan={2} style={{ textAlign: "right" }}>
                  {formatMoneyDisplay(query.data.total_expenses, currency)}
                </td>
              </tr>
            }
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
          <XAxis type="number" tick={{ fontSize: 12 }} />
          <YAxis
            type="category"
            dataKey="category"
            width={88}
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            formatter={(_value, _name, item) =>
              `${formatChartMoneyTooltip(String(item.payload.amount), currency)} · ${formatChartPercentTooltip(String(item.payload.percentage))}`
            }
          />
          <Bar dataKey="scale" name="Spending" fill="#0f766e" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </AnalyticsChartPanel>
  );
}
