import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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
import { Modal } from "@/components/ui/Modal";
import { useAccountsQuery } from "@/features/accounts/hooks";
import { useCategoriesQuery } from "@/features/categories/hooks";
import {
  formatRecurringFrequency,
  recurringStatusLabel,
  recurringStatusVariant,
} from "@/features/recurring-transactions/api";
import { RecurringTransactionEditForm } from "@/features/recurring-transactions/components/RecurringTransactionForm";
import {
  useArchiveRecurringTransactionMutation,
  useRecurringTransactionQuery,
  useSetRecurringTransactionActiveMutation,
  useUpdateRecurringTransactionMutation,
} from "@/features/recurring-transactions/hooks";
import { formatTransactionType } from "@/features/transactions/api";
import { formatMoneyDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

export function RecurringTransactionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [enabling, setEnabling] = useState(false);

  const recurringQuery = useRecurringTransactionQuery(id);
  const accountsQuery = useAccountsQuery({ status: "active", page_size: 100 });
  const categoriesQuery = useCategoriesQuery({
    status: "active",
    page_size: 100,
    include_system: true,
  });

  const updateMutation = useUpdateRecurringTransactionMutation();
  const archiveMutation = useArchiveRecurringTransactionMutation();
  const activeMutation = useSetRecurringTransactionActiveMutation();

  if (recurringQuery.isPending) {
    return (
      <PageContainer>
        <LoadingState title="Loading recurring transaction" />
      </PageContainer>
    );
  }

  if (recurringQuery.isError || !recurringQuery.data) {
    return (
      <PageContainer>
        <ErrorState
          error={recurringQuery.error}
          title="Unable to load recurring transaction"
          onRetry={() => void recurringQuery.refetch()}
        />
        <p>
          <Link to={routes.recurring}>Back to recurring transactions</Link>
        </p>
      </PageContainer>
    );
  }

  const recurring = recurringQuery.data;
  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];
  const accountName =
    accounts.find((account) => account.id === recurring.account_id)?.name ??
    recurring.account_id;
  const categoryName =
    categories.find((category) => category.id === recurring.category_id)?.name ??
    recurring.category_id;

  return (
    <PageContainer>
      <PageHeader
        title={recurring.description}
        description={`${formatRecurringFrequency(recurring.frequency)} · ${formatTransactionType(recurring.transaction_type)}`}
        actions={
          <div className="page-header__actions">
            <Link className="btn btn--secondary btn--sm" to={routes.recurring}>
              Back
            </Link>
            {recurring.is_active ? (
              <>
                <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
                  Edit
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setDisabling(true)}
                >
                  Disable
                </Button>
                <Button size="sm" variant="danger" onClick={() => setArchiving(true)}>
                  Archive
                </Button>
              </>
            ) : (
              <Button size="sm" variant="secondary" onClick={() => setEnabling(true)}>
                Enable
              </Button>
            )}
          </div>
        }
      />

      <div className="dashboard-grid">
        <Card>
          <CardHeader>
            <CardTitle>Schedule</CardTitle>
            <CardDescription>
              Status:{" "}
              <Badge variant={recurringStatusVariant(recurring.is_active)}>
                {recurringStatusLabel(recurring.is_active)}
              </Badge>
            </CardDescription>
          </CardHeader>
          <CardContent className="stack">
            <p className="stat-value">
              {formatMoneyDisplay(recurring.amount, recurring.currency)}
            </p>
            <dl className="dashboard-budget__stats">
              <div>
                <dt>Frequency</dt>
                <dd>{formatRecurringFrequency(recurring.frequency)}</dd>
              </div>
              <div>
                <dt>Next execution</dt>
                <dd>{recurring.next_execution_date}</dd>
              </div>
              <div>
                <dt>Start date</dt>
                <dd>{recurring.start_date}</dd>
              </div>
              <div>
                <dt>End date</dt>
                <dd>{recurring.end_date ?? "—"}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="stack">
            <p>Account: {accountName}</p>
            <p>Category: {categoryName}</p>
            <p>Type: {formatTransactionType(recurring.transaction_type)}</p>
            <p>Currency: {recurring.currency}</p>
            <p>Created: {recurring.created_at}</p>
            <p>Updated: {recurring.updated_at}</p>
          </CardContent>
        </Card>
      </div>

      <Modal
        open={editing}
        title="Edit recurring transaction"
        onClose={() => setEditing(false)}
      >
        <RecurringTransactionEditForm
          recurring={recurring}
          accounts={accounts}
          categories={categories}
          submitting={updateMutation.isPending}
          onCancel={() => setEditing(false)}
          onSubmit={async (payload) => {
            await updateMutation.mutateAsync({ id: recurring.id, payload });
            setEditing(false);
          }}
        />
      </Modal>

      <ConfirmDialog
        open={archiving}
        title="Archive recurring transaction?"
        description={`Archive “${recurring.description}”? It will stop executing on its schedule.`}
        confirmLabel="Archive"
        loading={archiveMutation.isPending}
        error={archiveMutation.error}
        onCancel={() => {
          archiveMutation.reset();
          setArchiving(false);
        }}
        onConfirm={() => {
          void archiveMutation.mutateAsync(recurring.id).then(() => {
            setArchiving(false);
            navigate(routes.recurring, { replace: true });
          });
        }}
      />

      <ConfirmDialog
        open={disabling}
        title="Disable recurring transaction?"
        description={`Disable “${recurring.description}”? You can enable it again later.`}
        confirmLabel="Disable"
        loading={activeMutation.isPending}
        error={activeMutation.error}
        onCancel={() => {
          activeMutation.reset();
          setDisabling(false);
        }}
        onConfirm={() => {
          void activeMutation
            .mutateAsync({ id: recurring.id, is_active: false })
            .then(() => {
              setDisabling(false);
            });
        }}
      />

      <ConfirmDialog
        open={enabling}
        title="Enable recurring transaction?"
        description={`Enable “${recurring.description}”? Scheduled executions will resume.`}
        confirmLabel="Enable"
        tone="primary"
        loading={activeMutation.isPending}
        error={activeMutation.error}
        onCancel={() => {
          activeMutation.reset();
          setEnabling(false);
        }}
        onConfirm={() => {
          void activeMutation
            .mutateAsync({ id: recurring.id, is_active: true })
            .then(() => {
              setEnabling(false);
            });
        }}
      />
    </PageContainer>
  );
}
