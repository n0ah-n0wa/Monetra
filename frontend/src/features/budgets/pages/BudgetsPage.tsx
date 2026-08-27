import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { FeaturePlaceholder } from "@/components/FeaturePlaceholder";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { fetchBudgets } from "@/features/budgets/api";
import { queryKeys } from "@/lib/query-client";

export function BudgetsPage() {
  const query = useQuery({
    queryKey: queryKeys.budgets.list(),
    queryFn: () => fetchBudgets({ page: 1, page_size: 1 }),
  });

  return (
    <FeaturePlaceholder
      title="Budgets"
      description="Set spending limits and monitor utilization over time."
    >
      {query.isPending ? <LoadingState title="Loading budgets" /> : null}
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess && query.data.total_items === 0 ? (
        <EmptyState
          title="No budgets yet"
          description="Create a budget to track spending targets."
        />
      ) : null}
      {query.isSuccess && query.data.total_items > 0 ? (
        <p>{query.data.total_items} active budget(s).</p>
      ) : null}
    </FeaturePlaceholder>
  );
}

export function BudgetDetailPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <FeaturePlaceholder
      title="Budget details"
      description={`Detailed view for budget ${id ?? ""}.`}
    />
  );
}
