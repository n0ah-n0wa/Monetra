import { useQuery } from "@tanstack/react-query";
import { FeaturePlaceholder } from "@/components/FeaturePlaceholder";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { fetchIncomeVsExpenses } from "@/features/analytics/api";
import { queryKeys } from "@/lib/query-client";
import { formatCurrency } from "@/lib/utils";

export function AnalyticsPage() {
  const query = useQuery({
    queryKey: queryKeys.analytics.incomeVsExpenses(),
    queryFn: () => fetchIncomeVsExpenses(),
  });

  return (
    <FeaturePlaceholder
      title="Analytics"
      description="Visualize cash flow, spending trends, and savings performance."
    >
      {query.isPending ? <LoadingState title="Loading analytics" /> : null}
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess ? (
        <p>
          Net for the current period:{" "}
          {formatCurrency(query.data.net_total, query.data.currency)}
        </p>
      ) : null}
    </FeaturePlaceholder>
  );
}
