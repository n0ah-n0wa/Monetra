import { Link } from "react-router-dom";
import {
  FinancialProgressBar,
  FinancialProgressStats,
} from "@/components/financial/FinancialProgress";
import { Badge } from "@/components/ui/Badge";
import { DashboardWidget } from "@/features/dashboard/components/DashboardWidget";
import { useBudgetUtilizationAnalyticsQuery } from "@/features/analytics/hooks";
import { budgetStatusVariant } from "@/features/budgets/api";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

export function BudgetUtilizationWidget() {
  const query = useBudgetUtilizationAnalyticsQuery();

  return (
    <DashboardWidget
      title="Budget utilization"
      description="Current month spending against your budgets."
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={query.isSuccess && query.data.items.length === 0}
      emptyTitle="No budgets configured"
      emptyDescription="Create a budget to track monthly spending limits."
      skeletonLines={4}
    >
      <div className="dashboard-list" role="list" aria-label="Budget utilization">
        {query.data?.items.map((item) => (
          <article key={item.budget.id} className="dashboard-budget" role="listitem">
            <div className="dashboard-budget__header">
              <p className="dashboard-budget__name">{item.budget.name}</p>
              <Badge variant={budgetStatusVariant(item.utilization.status)}>
                {item.utilization.status}
              </Badge>
            </div>
            <FinancialProgressBar
              percentage={item.utilization.percentage_used}
              label={`${item.budget.name} utilization`}
              status={item.utilization.status}
            />
            <FinancialProgressStats
              stats={[
                {
                  label: "Spent",
                  value: formatMoneyDisplay(
                    item.utilization.spent_amount,
                    item.budget.currency,
                  ),
                },
                {
                  label: "Budget",
                  value: formatMoneyDisplay(
                    item.utilization.budget_amount,
                    item.budget.currency,
                  ),
                },
                {
                  label: "Remaining",
                  value: formatMoneyDisplay(
                    item.utilization.remaining_amount,
                    item.budget.currency,
                  ),
                },
                {
                  label: "Used",
                  value: formatPercentDisplay(item.utilization.percentage_used),
                },
              ]}
            />
          </article>
        ))}
      </div>
      <p className="dashboard-widget__footer">
        <Link to={routes.budgets}>Manage budgets</Link>
      </p>
    </DashboardWidget>
  );
}
