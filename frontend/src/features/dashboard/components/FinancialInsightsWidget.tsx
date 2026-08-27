import type { UseQueryResult } from "@tanstack/react-query";
import { Alert } from "@/components/ui/Alert";
import {
  useBudgetUtilizationAnalyticsQuery,
  useLargestExpensesQuery,
  usePeriodComparisonQuery,
  useSavingsRateQuery,
  useSpendingByCategoryQuery,
} from "@/features/analytics/hooks";
import { DashboardWidget } from "@/features/dashboard/components/DashboardWidget";
import { buildFinancialInsights } from "@/features/dashboard/insights";

function queryHasData(query: Pick<UseQueryResult, "data" | "isSuccess">): boolean {
  return query.isSuccess && query.data !== undefined;
}

export function FinancialInsightsWidget() {
  const spendingQuery = useSpendingByCategoryQuery();
  const largestQuery = useLargestExpensesQuery();
  const comparisonQuery = usePeriodComparisonQuery();
  const savingsQuery = useSavingsRateQuery();
  const budgetsQuery = useBudgetUtilizationAnalyticsQuery();

  const queries = [
    spendingQuery,
    largestQuery,
    comparisonQuery,
    savingsQuery,
    budgetsQuery,
  ];

  const isLoading = queries.every((query) => query.isPending);
  const isError = queries.every((query) => query.isError);
  const hasPartialError = queries.some((query) => query.isError) && !isError;

  const insights = buildFinancialInsights({
    spendingByCategory: spendingQuery.data,
    largestExpenses: largestQuery.data,
    periodComparison: comparisonQuery.data,
    savingsRate: savingsQuery.data,
    budgetUtilization: budgetsQuery.data,
  });

  const firstError =
    spendingQuery.error ??
    largestQuery.error ??
    comparisonQuery.error ??
    savingsQuery.error ??
    budgetsQuery.error;

  function retryAll() {
    for (const query of queries) {
      if (query.isError || !queryHasData(query)) {
        void query.refetch();
      }
    }
  }

  return (
    <DashboardWidget
      title="Key financial insights"
      description="Highlights derived from your server-side analytics."
      isLoading={isLoading}
      isError={isError}
      error={firstError}
      onRetry={retryAll}
      isEmpty={!isLoading && !isError && insights.length === 0}
      emptyTitle="No insights yet"
      emptyDescription="Add transactions and budgets to unlock personalized insights."
      skeletonLines={4}
    >
      <div className="stack">
        {hasPartialError ? (
          <Alert variant="warning" title="Some insight data is unavailable">
            Showing available highlights. Retry to refresh missing analytics.
          </Alert>
        ) : null}
        <ul className="dashboard-insights" aria-label="Financial insights">
          {insights.map((insight) => (
            <li key={insight.id} className="dashboard-insights__item">
              <p className="dashboard-insights__title">{insight.title}</p>
              <p className="dashboard-insights__detail">{insight.detail}</p>
            </li>
          ))}
        </ul>
      </div>
    </DashboardWidget>
  );
}
