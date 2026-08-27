import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { useAccountsQuery } from "@/features/accounts/hooks";
import { useCategoriesQuery } from "@/features/categories/hooks";
import {
  formatRecurringFrequency,
  recurringStatusLabel,
  recurringStatusVariant,
  type RecurringTransaction,
} from "@/features/recurring-transactions/api";
import {
  RecurringTransactionCreateForm,
  RecurringTransactionEditForm,
} from "@/features/recurring-transactions/components/RecurringTransactionForm";
import {
  useArchiveRecurringTransactionMutation,
  useCreateRecurringTransactionMutation,
  useRecurringTransactionsQuery,
  useSetRecurringTransactionActiveMutation,
  useUpdateRecurringTransactionMutation,
} from "@/features/recurring-transactions/hooks";
import { formatTransactionType } from "@/features/transactions/api";
import { formatMoneyDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

type DialogState =
  | { type: "create" }
  | { type: "edit"; recurring: RecurringTransaction }
  | { type: "archive"; recurring: RecurringTransaction }
  | { type: "disable"; recurring: RecurringTransaction }
  | { type: "enable"; recurring: RecurringTransaction }
  | null;

type StatusFilter = "all" | "active" | "inactive";

function resolveAccountName(accountId: string, accounts: Map<string, string>): string {
  return accounts.get(accountId) ?? "Unknown account";
}

function resolveCategoryName(
  categoryId: string,
  categories: Map<string, string>,
): string {
  return categories.get(categoryId) ?? "Unknown category";
}

export function RecurringTransactionsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [dialog, setDialog] = useState<DialogState>(null);

  const listParams = useMemo(
    () => ({
      page: 1,
      page_size: 100,
      is_active: statusFilter === "all" ? undefined : statusFilter === "active",
    }),
    [statusFilter],
  );

  const recurringQuery = useRecurringTransactionsQuery(listParams);
  const accountsQuery = useAccountsQuery({ status: "active", page_size: 100 });
  const categoriesQuery = useCategoriesQuery({
    status: "active",
    page_size: 100,
    include_system: true,
  });

  const createMutation = useCreateRecurringTransactionMutation();
  const archiveMutation = useArchiveRecurringTransactionMutation();
  const activeMutation = useSetRecurringTransactionActiveMutation();

  const editingRecurring = dialog?.type === "edit" ? dialog.recurring : null;
  const updateMutation = useUpdateRecurringTransactionMutation();

  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];

  const accountNames = useMemo(() => {
    const items = accountsQuery.data?.items ?? [];
    return new Map(items.map((account) => [account.id, account.name]));
  }, [accountsQuery.data?.items]);
  const categoryNames = useMemo(() => {
    const items = categoriesQuery.data?.items ?? [];
    return new Map(items.map((category) => [category.id, category.name]));
  }, [categoriesQuery.data?.items]);

  const referenceDataLoading = accountsQuery.isPending || categoriesQuery.isPending;
  const referenceDataError = accountsQuery.isError || categoriesQuery.isError;

  return (
    <PageContainer>
      <PageHeader
        title="Recurring transactions"
        description="Automate income and expenses on a schedule."
        actions={
          <Button
            onClick={() => setDialog({ type: "create" })}
            disabled={referenceDataLoading || accounts.length === 0}
          >
            Add recurring transaction
          </Button>
        }
      />

      <div className="toolbar">
        <label className="toolbar__filter" htmlFor="recurring-status-filter">
          <span>Status</span>
          <Select
            id="recurring-status-filter"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="all">All</option>
          </Select>
        </label>
      </div>

      {referenceDataError ? (
        <Alert variant="warning" title="Reference data unavailable">
          Account and category names may be missing.{" "}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              void accountsQuery.refetch();
              void categoriesQuery.refetch();
            }}
          >
            Retry
          </Button>
        </Alert>
      ) : null}

      {recurringQuery.isPending ? (
        <LoadingState title="Loading recurring transactions" />
      ) : null}
      {recurringQuery.isError ? (
        <ErrorState
          error={recurringQuery.error}
          title="Unable to load recurring transactions"
          onRetry={() => void recurringQuery.refetch()}
        />
      ) : null}

      {recurringQuery.isSuccess && recurringQuery.data.items.length === 0 ? (
        <EmptyState
          title="No recurring transactions"
          description={
            accounts.length === 0
              ? "Create an account first, then add a recurring schedule."
              : "Create a recurring transaction to automate scheduled income or expenses."
          }
        />
      ) : null}

      {recurringQuery.isSuccess && recurringQuery.data.items.length > 0 ? (
        <div className="data-list" role="list">
          {recurringQuery.data.items.map((recurring) => (
            <article key={recurring.id} className="data-card" role="listitem">
              <div className="data-card__main">
                <div className="data-card__title-row">
                  <Link
                    className="data-card__title"
                    to={routes.recurringDetail(recurring.id)}
                  >
                    {recurring.description}
                  </Link>
                  <Badge variant={recurringStatusVariant(recurring.is_active)}>
                    {recurringStatusLabel(recurring.is_active)}
                  </Badge>
                </div>
                <p className="data-card__meta">
                  {formatRecurringFrequency(recurring.frequency)} ·{" "}
                  {formatTransactionType(recurring.transaction_type)}
                </p>
                <p className="data-card__value">
                  {formatMoneyDisplay(recurring.amount, recurring.currency)}
                </p>
                <dl className="dashboard-budget__stats">
                  <div>
                    <dt>Account</dt>
                    <dd>{resolveAccountName(recurring.account_id, accountNames)}</dd>
                  </div>
                  <div>
                    <dt>Category</dt>
                    <dd>{resolveCategoryName(recurring.category_id, categoryNames)}</dd>
                  </div>
                  <div>
                    <dt>Next execution</dt>
                    <dd>{recurring.next_execution_date}</dd>
                  </div>
                </dl>
              </div>
              <div className="data-card__actions">
                <Link
                  className="btn btn--secondary btn--sm"
                  to={routes.recurringDetail(recurring.id)}
                >
                  View
                </Link>
                {recurring.is_active ? (
                  <>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setDialog({ type: "edit", recurring })}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setDialog({ type: "disable", recurring })}
                    >
                      Disable
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => setDialog({ type: "archive", recurring })}
                    >
                      Archive
                    </Button>
                  </>
                ) : (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setDialog({ type: "enable", recurring })}
                  >
                    Enable
                  </Button>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : null}

      <Modal
        open={dialog?.type === "create"}
        title="Create recurring transaction"
        description="Define a schedule that creates transactions automatically."
        onClose={() => setDialog(null)}
      >
        <RecurringTransactionCreateForm
          accounts={accounts}
          categories={categories}
          submitting={createMutation.isPending}
          onCancel={() => setDialog(null)}
          onSubmit={async (payload) => {
            await createMutation.mutateAsync(payload);
            setDialog(null);
          }}
        />
      </Modal>

      <Modal
        open={dialog?.type === "edit"}
        title="Edit recurring transaction"
        onClose={() => setDialog(null)}
      >
        {editingRecurring ? (
          <RecurringTransactionEditForm
            recurring={editingRecurring}
            accounts={accounts}
            categories={categories}
            submitting={updateMutation.isPending}
            onCancel={() => setDialog(null)}
            onSubmit={async (payload) => {
              await updateMutation.mutateAsync({
                id: editingRecurring.id,
                payload,
              });
              setDialog(null);
            }}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={dialog?.type === "archive"}
        title="Archive recurring transaction?"
        description={
          dialog?.type === "archive"
            ? `Archive “${dialog.recurring.description}”? It will stop executing on its schedule.`
            : ""
        }
        confirmLabel="Archive"
        loading={archiveMutation.isPending}
        error={archiveMutation.error}
        onCancel={() => {
          archiveMutation.reset();
          setDialog(null);
        }}
        onConfirm={() => {
          if (dialog?.type !== "archive") {
            return;
          }
          void archiveMutation.mutateAsync(dialog.recurring.id).then(() => {
            setDialog(null);
          });
        }}
      />

      <ConfirmDialog
        open={dialog?.type === "disable"}
        title="Disable recurring transaction?"
        description={
          dialog?.type === "disable"
            ? `Disable “${dialog.recurring.description}”? You can enable it again later.`
            : ""
        }
        confirmLabel="Disable"
        loading={activeMutation.isPending}
        error={activeMutation.error}
        onCancel={() => {
          activeMutation.reset();
          setDialog(null);
        }}
        onConfirm={() => {
          if (dialog?.type !== "disable") {
            return;
          }
          void activeMutation
            .mutateAsync({ id: dialog.recurring.id, is_active: false })
            .then(() => {
              setDialog(null);
            });
        }}
      />

      <ConfirmDialog
        open={dialog?.type === "enable"}
        title="Enable recurring transaction?"
        description={
          dialog?.type === "enable"
            ? `Enable “${dialog.recurring.description}”? Scheduled executions will resume.`
            : ""
        }
        confirmLabel="Enable"
        tone="primary"
        loading={activeMutation.isPending}
        error={activeMutation.error}
        onCancel={() => {
          activeMutation.reset();
          setDialog(null);
        }}
        onConfirm={() => {
          if (dialog?.type !== "enable") {
            return;
          }
          void activeMutation
            .mutateAsync({ id: dialog.recurring.id, is_active: true })
            .then(() => {
              setDialog(null);
            });
        }}
      />
    </PageContainer>
  );
}
