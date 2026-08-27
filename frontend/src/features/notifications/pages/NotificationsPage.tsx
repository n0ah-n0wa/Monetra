import { useQuery } from "@tanstack/react-query";
import { FeaturePlaceholder } from "@/components/FeaturePlaceholder";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { fetchNotifications } from "@/features/notifications/api";
import { queryKeys } from "@/lib/query-client";

export function NotificationsPage() {
  const query = useQuery({
    queryKey: queryKeys.notifications.list(),
    queryFn: () => fetchNotifications({ page: 1, page_size: 5 }),
  });

  return (
    <FeaturePlaceholder
      title="Notifications"
      description="Stay informed about budgets, goals, imports, and recurring activity."
    >
      {query.isPending ? <LoadingState title="Loading notifications" /> : null}
      {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.isSuccess && query.data.total_items === 0 ? (
        <EmptyState title="No notifications" description="You're all caught up." />
      ) : null}
      {query.isSuccess && query.data.total_items > 0 ? (
        <p>{query.data.total_items} notification(s) in your inbox.</p>
      ) : null}
    </FeaturePlaceholder>
  );
}
