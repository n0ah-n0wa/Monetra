import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { FeaturePlaceholder } from "@/components/FeaturePlaceholder";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { fetchTransactions } from "@/features/transactions/api";
import { queryKeys } from "@/lib/query-client";

export function TransactionsPage() {
  const query = useQuery({
    queryKey: queryKeys.transactions.list(),
    queryFn: () => fetchTransactions({ page: 1, page_size: 1 }),
  });

  return (
    <FeaturePlaceholder
      title="Transactions"
      description="Review income, expenses, and transfers across accounts."
    >
      {query.isPending ? <LoadingState title="Loading transactions" /> : null}
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess && query.data.total_items === 0 ? (
        <EmptyState
          title="No transactions yet"
          description="Recorded activity will appear here once you add transactions."
        />
      ) : null}
      {query.isSuccess && query.data.total_items > 0 ? (
        <p>{query.data.total_items} transaction(s) on record.</p>
      ) : null}
    </FeaturePlaceholder>
  );
}

export function TransactionCreatePage() {
  return (
    <FeaturePlaceholder
      title="Add transaction"
      description="Fast transaction entry will be implemented in a dedicated screen."
    />
  );
}

export function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <FeaturePlaceholder
      title="Transaction details"
      description={`Detailed view for transaction ${id ?? ""}.`}
    />
  );
}
