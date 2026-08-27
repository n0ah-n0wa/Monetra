import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { Alert } from "@/components/ui/Alert";
import { useAccountsQuery } from "@/features/accounts/hooks";
import { useCategoriesQuery } from "@/features/categories/hooks";
import {
  TransactionForm,
  transactionFormToCreatePayload,
} from "@/features/transactions/components/TransactionForm";
import { useCreateTransactionMutation } from "@/features/transactions/hooks";
import { routes } from "@/lib/routes";

export function TransactionCreatePage() {
  const navigate = useNavigate();
  const [savedCount, setSavedCount] = useState(0);
  const accountsQuery = useAccountsQuery({ status: "active", page_size: 100 });
  const categoriesQuery = useCategoriesQuery({
    status: "active",
    page_size: 100,
    include_system: true,
  });
  const createMutation = useCreateTransactionMutation();

  if (accountsQuery.isPending || categoriesQuery.isPending) {
    return (
      <PageContainer>
        <LoadingState title="Preparing transaction form" />
      </PageContainer>
    );
  }

  if (accountsQuery.isError || categoriesQuery.isError) {
    return (
      <PageContainer>
        <ErrorState
          error={accountsQuery.error ?? categoriesQuery.error}
          title="Unable to load form data"
          onRetry={() => {
            void accountsQuery.refetch();
            void categoriesQuery.refetch();
          }}
        />
      </PageContainer>
    );
  }

  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];

  if (accounts.length === 0) {
    return (
      <PageContainer>
        <PageHeader
          title="Add transaction"
          description="Create an account before recording transactions."
        />
        <Alert variant="warning" title="No accounts available">
          <Link to={routes.accounts}>Create an account</Link> to continue.
        </Alert>
      </PageContainer>
    );
  }

  return (
    <PageContainer narrow>
      <PageHeader
        title="Add transaction"
        description="Optimized for fast repeated entry. Amount, description, and notes reset after each save."
        actions={
          <Link className="btn btn--secondary btn--sm" to={routes.transactions}>
            Back to list
          </Link>
        }
      />

      {savedCount > 0 ? (
        <Alert variant="success" title="Transactions saved">
          {savedCount} transaction{savedCount === 1 ? "" : "s"} recorded this session.
        </Alert>
      ) : null}

      <TransactionForm
        mode="create"
        accounts={accounts}
        categories={categories}
        submitting={createMutation.isPending}
        focusAmountOnMount
        showAddAnother
        onSubmit={async (values, options) => {
          await createMutation.mutateAsync(transactionFormToCreatePayload(values));
          setSavedCount((count) => count + 1);
          if (!options?.addAnother) {
            navigate(routes.transactions);
          }
        }}
        onCancel={() => navigate(routes.transactions)}
      />
    </PageContainer>
  );
}
