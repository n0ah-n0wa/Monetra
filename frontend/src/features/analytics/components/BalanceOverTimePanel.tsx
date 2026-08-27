import {
  CartesianGrid,
  Line,
  LineChart,
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
import { useBalanceOverTimeQuery } from "@/features/analytics/hooks";
import { formatMoneyDisplay } from "@/lib/money";

type PanelProps = {
  params: AnalyticsQueryParams;
  enabled?: boolean;
};

export function BalanceOverTimePanel({ params, enabled = true }: PanelProps) {
  const query = useBalanceOverTimeQuery(params, { enabled });
  const currency = query.data?.reporting_currency ?? params.reporting_currency ?? "USD";

  const chartData =
    query.data?.points.map((point) => ({
      date: point.bucket_date,
      balance: point.balance,
      scale: chartScaleValue(point.balance),
    })) ?? [];

  return (
    <AnalyticsChartPanel
      title="Balance over time"
      description="Derived balances from server-side ledger aggregation."
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={query.isSuccess && chartData.length === 0}
      emptyTitle="No balance history"
      emptyDescription="Balances appear once accounts have activity in this period."
      table={
        query.data ? (
          <AccessibleDataTable
            caption="Balance over time for the selected period"
            columns={[
              { key: "date", header: "Date", cell: (row) => row.bucket_date },
              {
                key: "balance",
                header: "Balance",
                align: "right",
                cell: (row) => formatMoneyDisplay(row.balance, currency),
              },
            ]}
            rows={query.data.points}
            getRowKey={(row) => row.bucket_date}
            footer={
              <tr>
                <th scope="row">Opening</th>
                <td style={{ textAlign: "right" }}>
                  {formatMoneyDisplay(query.data.opening_balance, currency)}
                </td>
              </tr>
            }
          />
        ) : null
      }
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
          <YAxis tick={{ fontSize: 12 }} width={48} />
          <Tooltip
            formatter={(_value, _name, item) =>
              formatChartMoneyTooltip(String(item.payload.balance), currency, "Balance")
            }
            labelFormatter={(label) => `Date: ${label}`}
          />
          <Line
            type="monotone"
            dataKey="scale"
            name="Balance"
            stroke="var(--brand)"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </AnalyticsChartPanel>
  );
}
