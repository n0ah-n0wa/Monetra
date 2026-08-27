import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { FeaturePlaceholder } from "@/components/FeaturePlaceholder";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { fetchAccounts } from "@/features/accounts/api";
import { queryKeys } from "@/lib/query-client";

export function AccountsPage() {
  const query = useQuery({
    queryKey: queryKeys.accounts.list(),
    queryFn: () => fetchAccounts({ page: 1, page_size: 1 }),
  });

  return (
    <FeaturePlaceholder
      title="Accounts"
      description="Manage cash, checking, savings, and other financial accounts."
    >
      {query.isPending ? <LoadingState title="Loading accounts" /> : null}
      {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.isSuccess && query.data.total_items === 0 ? (
        <EmptyState
          title="No accounts yet"
          description="Create your first account to start tracking balances."
        />
      ) : null}
      {query.isSuccess && query.data.total_items > 0 ? (
        <p>{query.data.total_items} account(s) connected.</p>
      ) : null}
    </FeaturePlaceholder>
  );
}

export function AccountDetailPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <FeaturePlaceholder
      title="Account details"
      description={`Detailed view for account ${id ?? ""}.`}
    />
  );
}
