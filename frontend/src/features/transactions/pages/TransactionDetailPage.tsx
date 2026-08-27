import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useAccountsQuery } from "@/features/accounts/hooks";
import { useCategoriesQuery } from "@/features/categories/hooks";
import { TransactionForm } from "@/features/transactions/components/TransactionForm";
import { transactionFormToUpdatePayload } from "@/features/transactions/transaction-form-payload";
import { formatTransactionType } from "@/features/transactions/api";
import {
  useDeleteTransactionMutation,
  useTransactionQuery,
  useUpdateTransactionMutation,
} from "@/features/transactions/hooks";
import { formatMoneyDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

export function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const transactionQuery = useTransactionQuery(id);
  const accountsQuery = useAccountsQuery({ status: "active", page_size: 100 });
  const categoriesQuery = useCategoriesQuery({
    status: "active",
    page_size: 100,
    include_system: true,
  });
  const updateMutation = useUpdateTransactionMutation(id ?? "");
  const deleteMutation = useDeleteTransactionMutation();

  if (
    transactionQuery.isPending ||
    accountsQuery.isPending ||
    categoriesQuery.isPending
  ) {
    return (
      <PageContainer>
        <LoadingState title="Loading transaction" />
      </PageContainer>
    );
  }

  if (transactionQuery.isError || !transactionQuery.data) {
    return (
      <PageContainer>
        <ErrorState
          error={transactionQuery.error}
          title="Unable to load transaction"
          onRetry={() => void transactionQuery.refetch()}
        />
        <p>
          <Link to={routes.transactions}>Back to transactions</Link>
        </p>
      </PageContainer>
    );
  }

  const transaction = transactionQuery.data;
  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];
  const accountName =
    accounts.find((account) => account.id === transaction.account_id)?.name ??
    transaction.account_id;
  const categoryName =
    categories.find((category) => category.id === transaction.category_id)?.name ??
    transaction.category_id;
  const referenceDataFailed = accountsQuery.isError || categoriesQuery.isError;

  return (
    <PageContainer>
      <PageHeader
        title={transaction.description}
        description={`${transaction.transaction_date} · ${formatTransactionType(transaction.transaction_type)}`}
        actions={
          <div className="page-header__actions">
            <Link className="btn btn--secondary btn--sm" to={routes.transactions}>
              Back
            </Link>
            <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
              Edit
            </Button>
            <Button size="sm" variant="danger" onClick={() => setDeleting(true)}>
              Delete
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Transaction details</CardTitle>
          <CardDescription>
            Amounts are stored and calculated exactly on the server.
          </CardDescription>
        </CardHeader>
        <CardContent className="stack">
          <p className="stat-value">
            {formatMoneyDisplay(transaction.amount, transaction.currency)}
          </p>
          <p>
            Type:{" "}
            <Badge
              variant={
                transaction.transaction_type === "income" ? "success" : "neutral"
              }
            >
              {formatTransactionType(transaction.transaction_type)}
            </Badge>
          </p>
          <p>Date: {transaction.transaction_date}</p>
          <p>Account: {accountName}</p>
          <p>Category: {categoryName}</p>
          <p>Currency: {transaction.currency}</p>
          {transaction.notes ? <p>Notes: {transaction.notes}</p> : null}
        </CardContent>
      </Card>

      {editing ? (
        <Card>
          <CardHeader>
            <CardTitle>Edit transaction</CardTitle>
          </CardHeader>
          <CardContent>
            {referenceDataFailed ? (
              <Alert variant="warning" title="Form data unavailable">
                Unable to load accounts or categories. Try again before editing.
              </Alert>
            ) : (
              <TransactionForm
                mode="edit"
                accounts={accounts}
                categories={categories}
                transaction={transaction}
                submitting={updateMutation.isPending}
                onSubmit={async (values) => {
                  await updateMutation.mutateAsync(
                    transactionFormToUpdatePayload(values),
                  );
                  setEditing(false);
                }}
                onCancel={() => setEditing(false)}
              />
            )}
          </CardContent>
        </Card>
      ) : null}

      <ConfirmDialog
        open={deleting}
        title="Delete transaction?"
        description={`Delete “${transaction.description}”? The account balance will be adjusted on the server.`}
        confirmLabel="Delete transaction"
        loading={deleteMutation.isPending}
        error={deleteMutation.error}
        onCancel={() => {
          deleteMutation.reset();
          setDeleting(false);
        }}
        onConfirm={() => {
          void deleteMutation.mutateAsync(transaction.id).then(() => {
            navigate(routes.transactions, { replace: true });
          });
        }}
      />
    </PageContainer>
  );
}
