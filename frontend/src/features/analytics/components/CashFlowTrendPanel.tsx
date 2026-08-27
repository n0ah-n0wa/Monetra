import {
  CartesianGrid,
  Legend,
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
import { useNetCashFlowQuery } from "@/features/analytics/hooks";
import { formatMoneyDisplay } from "@/lib/money";

type PanelProps = {
  params: AnalyticsQueryParams;
  enabled?: boolean;
};

export function CashFlowTrendPanel({ params, enabled = true }: PanelProps) {
  const query = useNetCashFlowQuery(params, { enabled });
  const currency = query.data?.reporting_currency ?? params.reporting_currency ?? "USD";

  const chartData =
    query.data?.points.map((point) => ({
      date: point.bucket_date,
      net_cash_flow: point.net_cash_flow,
      income: point.income,
      expenses: point.expenses,
      netScale: chartScaleValue(point.net_cash_flow),
      incomeScale: chartScaleValue(point.income),
      expenseScale: chartScaleValue(point.expenses),
    })) ?? [];

  return (
    <AnalyticsChartPanel
      title="Cash flow trend"
      description="Net cash flow buckets from server analytics."
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={query.isSuccess && chartData.length === 0}
      emptyTitle="No cash flow data"
      emptyDescription="Transactions in this period will populate the trend."
      table={
        query.data ? (
          <AccessibleDataTable
            caption="Cash flow trend for the selected period"
            columns={[
              { key: "date", header: "Date", cell: (row) => row.bucket_date },
              {
                key: "income",
                header: "Income",
                align: "right",
                cell: (row) => formatMoneyDisplay(row.income, currency),
              },
              {
                key: "expenses",
                header: "Expenses",
                align: "right",
                cell: (row) => formatMoneyDisplay(row.expenses, currency),
              },
              {
                key: "net",
                header: "Net",
                align: "right",
                cell: (row) => formatMoneyDisplay(row.net_cash_flow, currency),
              },
            ]}
            rows={query.data.points}
            getRowKey={(row) => row.bucket_date}
            footer={
              <tr>
                <th scope="row">Total net cash flow</th>
                <td colSpan={3} style={{ textAlign: "right" }}>
                  {formatMoneyDisplay(query.data.total_net_cash_flow, currency)}
                </td>
              </tr>
            }
          />
        ) : null
      }
    >
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
          <YAxis tick={{ fontSize: 12 }} width={48} />
          <Tooltip
            formatter={(_value, name, item) => {
              const payload = item.payload as {
                income: string;
                expenses: string;
                net_cash_flow: string;
              };
              if (name === "Income") {
                return formatChartMoneyTooltip(payload.income, currency);
              }
              if (name === "Expenses") {
                return formatChartMoneyTooltip(payload.expenses, currency);
              }
              return formatChartMoneyTooltip(payload.net_cash_flow, currency, "Net");
            }}
            labelFormatter={(label) => `Date: ${label}`}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="incomeScale"
            name="Income"
            stroke="#0f766e"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="expenseScale"
            name="Expenses"
            stroke="#b45309"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="netScale"
            name="Net cash flow"
            stroke="var(--brand)"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </AnalyticsChartPanel>
  );
}
