import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/Badge";
import {
  useBalanceOverTimeQuery,
  useIncomeVsExpensesQuery,
  useNetCashFlowQuery,
  useSavingsRateQuery,
} from "@/features/analytics/hooks";
import { DashboardStatCard } from "@/features/dashboard/components/DashboardWidget";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

export function SummaryStatsRow() {
  const balanceQuery = useBalanceOverTimeQuery();
  const incomeExpensesQuery = useIncomeVsExpensesQuery();
  const cashFlowQuery = useNetCashFlowQuery();
  const savingsQuery = useSavingsRateQuery();

  const currency =
    balanceQuery.data?.reporting_currency ??
    incomeExpensesQuery.data?.reporting_currency ??
    cashFlowQuery.data?.reporting_currency ??
    savingsQuery.data?.reporting_currency ??
    "USD";

  return (
    <section className="dashboard-stats" aria-label="Financial summary">
      <DashboardStatCard
        label="Total balance"
        value={
          balanceQuery.data
            ? formatMoneyDisplay(balanceQuery.data.closing_balance, currency)
            : "—"
        }
        hint={
          balanceQuery.data ? `As of ${balanceQuery.data.period.end_date}` : undefined
        }
        isLoading={balanceQuery.isPending}
        isError={balanceQuery.isError}
        error={balanceQuery.error}
        onRetry={() => void balanceQuery.refetch()}
      />
      <DashboardStatCard
        label="Monthly income"
        value={
          incomeExpensesQuery.data
            ? formatMoneyDisplay(incomeExpensesQuery.data.income, currency)
            : "—"
        }
        isLoading={incomeExpensesQuery.isPending}
        isError={incomeExpensesQuery.isError}
        error={incomeExpensesQuery.error}
        onRetry={() => void incomeExpensesQuery.refetch()}
      />
      <DashboardStatCard
        label="Monthly expenses"
        value={
          incomeExpensesQuery.data
            ? formatMoneyDisplay(incomeExpensesQuery.data.expenses, currency)
            : "—"
        }
        isLoading={incomeExpensesQuery.isPending}
        isError={incomeExpensesQuery.isError}
        error={incomeExpensesQuery.error}
        onRetry={() => void incomeExpensesQuery.refetch()}
      />
      <DashboardStatCard
        label="Net cash flow"
        value={
          cashFlowQuery.data
            ? formatMoneyDisplay(cashFlowQuery.data.total_net_cash_flow, currency)
            : "—"
        }
        isLoading={cashFlowQuery.isPending}
        isError={cashFlowQuery.isError}
        error={cashFlowQuery.error}
        onRetry={() => void cashFlowQuery.refetch()}
      />
      <DashboardStatCard
        label="Savings rate"
        value={formatPercentDisplay(savingsQuery.data?.savings_rate_percent)}
        hint={
          savingsQuery.data?.savings_rate_percent === null
            ? "No income recorded this month"
            : undefined
        }
        isLoading={savingsQuery.isPending}
        isError={savingsQuery.isError}
        error={savingsQuery.error}
        onRetry={() => void savingsQuery.refetch()}
      />
    </section>
  );
}

export function SummaryStatsLinks() {
  return (
    <p className="dashboard-period-note">
      Summary reflects the <Badge variant="neutral">current month</Badge> in your
      reporting currency. <Link to={routes.analytics}>View full analytics</Link>
    </p>
  );
}
