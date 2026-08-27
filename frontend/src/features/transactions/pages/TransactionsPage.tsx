import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useAccountsQuery } from "@/features/accounts/hooks";
import { useCategoriesQuery } from "@/features/categories/hooks";
import {
  TransactionFilters,
  TransactionPagination,
  defaultTransactionFilters,
  filtersToQueryParams,
  type TransactionFilterState,
} from "@/features/transactions/components/TransactionFilters";
import { TransactionList } from "@/features/transactions/components/TransactionList";
import type { Transaction } from "@/features/transactions/api";
import {
  useDeleteTransactionMutation,
  useTransactionsQuery,
} from "@/features/transactions/hooks";
import { routes } from "@/lib/routes";
import { formatMoneyDisplay } from "@/lib/money";
import { useDebouncedValue } from "@/lib/useDebouncedValue";

export function TransactionsPage() {
  const [filters, setFilters] = useState<TransactionFilterState>(
    defaultTransactionFilters,
  );
  const [deleting, setDeleting] = useState<Transaction | null>(null);

  const debouncedDescription = useDebouncedValue(filters.description, 300);
  const queryParams = useMemo(
    () => filtersToQueryParams({ ...filters, description: debouncedDescription }),
    [filters, debouncedDescription],
  );
  const transactionsQuery = useTransactionsQuery(queryParams);
  const accountsQuery = useAccountsQuery({ status: "active", page_size: 100 });
  const categoriesQuery = useCategoriesQuery({
    status: "active",
    page_size: 100,
    include_system: true,
  });
  const deleteMutation = useDeleteTransactionMutation();

  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];

  return (
    <PageContainer>
      <PageHeader
        title="Transactions"
        description="Review, filter, and manage income and expenses across accounts."
        actions={
          <Link className="btn btn--primary btn--md" to={routes.transactionNew}>
            Add transaction
          </Link>
        }
      />

      <TransactionFilters
        filters={filters}
        accounts={accounts}
        categories={categories}
        onChange={setFilters}
        onReset={() => setFilters(defaultTransactionFilters)}
      />

      {accountsQuery.isError || categoriesQuery.isError ? (
        <Alert variant="warning" title="Reference data unavailable">
          Some filter options may be missing.{" "}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              void accountsQuery.refetch();
              void categoriesQuery.refetch();
            }}
          >
            Retry loading accounts and categories
          </Button>
        </Alert>
      ) : null}

      {transactionsQuery.isPending ? (
        <LoadingState title="Loading transactions" />
      ) : null}
      {transactionsQuery.isError ? (
        <ErrorState
          error={transactionsQuery.error}
          title="Unable to load transactions"
          onRetry={() => void transactionsQuery.refetch()}
        />
      ) : null}

      {transactionsQuery.isSuccess && transactionsQuery.data.items.length === 0 ? (
        <EmptyState
          title="No transactions found"
          description="Adjust filters or record your first transaction."
        />
      ) : null}

      {transactionsQuery.isSuccess && transactionsQuery.data.items.length > 0 ? (
        <>
          <TransactionList
            transactions={transactionsQuery.data.items}
            accounts={accounts}
            categories={categories}
            onDelete={setDeleting}
          />
          <TransactionPagination
            page={transactionsQuery.data.page}
            totalPages={transactionsQuery.data.total_pages}
            totalItems={transactionsQuery.data.total_items}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
          />
        </>
      ) : null}

      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete transaction?"
        description={
          deleting
            ? `Delete “${deleting.description}” for ${formatMoneyDisplay(deleting.amount, deleting.currency)}? This reverses the balance impact on the server.`
            : ""
        }
        confirmLabel="Delete transaction"
        loading={deleteMutation.isPending}
        error={deleteMutation.error}
        onCancel={() => {
          deleteMutation.reset();
          setDeleting(null);
        }}
        onConfirm={() => {
          if (!deleting) {
            return;
          }
          void deleteMutation.mutateAsync(deleting.id).then(() => {
            setDeleting(null);
          });
        }}
      />
    </PageContainer>
  );
}
