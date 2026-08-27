import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { FeaturePlaceholder } from "@/components/FeaturePlaceholder";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { fetchGoals } from "@/features/goals/api";
import { queryKeys } from "@/lib/query-client";

export function GoalsPage() {
  const query = useQuery({
    queryKey: queryKeys.goals.list(),
    queryFn: () => fetchGoals({ page: 1, page_size: 1 }),
  });

  return (
    <FeaturePlaceholder
      title="Goals"
      description="Track savings targets and milestone progress."
    >
      {query.isPending ? <LoadingState title="Loading goals" /> : null}
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess && query.data.total_items === 0 ? (
        <EmptyState
          title="No goals yet"
          description="Savings goals will be created and tracked here."
        />
      ) : null}
      {query.isSuccess && query.data.total_items > 0 ? (
        <p>{query.data.total_items} goal(s) in progress.</p>
      ) : null}
    </FeaturePlaceholder>
  );
}

export function GoalDetailPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <FeaturePlaceholder
      title="Goal details"
      description={`Detailed view for goal ${id ?? ""}.`}
    />
  );
}
