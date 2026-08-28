import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
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
import {
  AccountCreateForm,
  AccountEditForm,
} from "@/features/accounts/components/AccountForm";
import {
  formatAccountType,
  type Account,
  type AccountStatus,
} from "@/features/accounts/api";
import {
  useAccountsQuery,
  useArchiveAccountMutation,
  useCreateAccountMutation,
  useUpdateAccountMutation,
} from "@/features/accounts/hooks";
import { useAuth } from "@/features/auth/hooks";
import { formatMoneyDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

type DialogState =
  | { type: "create" }
  | { type: "edit"; account: Account }
  | { type: "archive"; account: Account }
  | null;

export function AccountsPage() {
  const { user } = useAuth();
  const [statusFilter, setStatusFilter] = useState<AccountStatus | "all">("active");
  const [dialog, setDialog] = useState<DialogState>(null);

  const listParams = useMemo(
    () => ({
      page: 1,
      page_size: 100,
      status: statusFilter === "all" ? undefined : statusFilter,
    }),
    [statusFilter],
  );

  const accountsQuery = useAccountsQuery(listParams);
  const createMutation = useCreateAccountMutation();
  const archiveMutation = useArchiveAccountMutation();

  const editingAccount = dialog?.type === "edit" ? dialog.account : null;
  const updateMutation = useUpdateAccountMutation(editingAccount?.id ?? "");

  return (
    <PageContainer>
      <PageHeader
        title="Accounts"
        description="Track balances across cash, bank, savings, and credit accounts."
        actions={
          <Button onClick={() => setDialog({ type: "create" })}>Add account</Button>
        }
      />

      <div className="toolbar">
        <label className="toolbar__filter" htmlFor="account-status-filter">
          <span>Status</span>
          <Select
            id="account-status-filter"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value as AccountStatus | "all")
            }
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </Select>
        </label>
      </div>

      {accountsQuery.isPending ? <LoadingState title="Loading accounts" /> : null}
      {accountsQuery.isError ? (
        <ErrorState
          error={accountsQuery.error}
          title="Unable to load accounts"
          onRetry={() => void accountsQuery.refetch()}
        />
      ) : null}

      {accountsQuery.isSuccess && accountsQuery.data.items.length === 0 ? (
        <EmptyState
          title="No accounts yet"
          description="Create your first account to start tracking balances."
          actionLabel="Add account"
          onAction={() => setDialog({ type: "create" })}
        />
      ) : null}

      {accountsQuery.isSuccess && accountsQuery.data.items.length > 0 ? (
        <div className="data-list" role="list">
          {accountsQuery.data.items.map((account) => (
            <article key={account.id} className="data-card" role="listitem">
              <div className="data-card__main">
                <div className="data-card__title-row">
                  <Link
                    className="data-card__title"
                    to={routes.accountDetail(account.id)}
                  >
                    {account.name}
                  </Link>
                  <Badge variant={account.status === "active" ? "success" : "neutral"}>
                    {account.status}
                  </Badge>
                </div>
                <p className="data-card__meta">
                  {formatAccountType(account.account_type)} · {account.currency}
                </p>
                <p className="data-card__value">
                  {formatMoneyDisplay(account.current_balance, account.currency)}
                </p>
              </div>
              <div className="data-card__actions">
                {account.status === "active" ? (
                  <>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setDialog({ type: "edit", account })}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => setDialog({ type: "archive", account })}
                    >
                      Archive
                    </Button>
                  </>
                ) : (
                  <Link
                    className="btn btn--secondary btn--sm"
                    to={routes.accountDetail(account.id)}
                  >
                    View
                  </Link>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : null}

      <Modal
        open={dialog?.type === "create"}
        title="Create account"
        description="Opening balance and currency are fixed after creation."
        onClose={() => setDialog(null)}
      >
        <AccountCreateForm
          defaultCurrency={user?.reporting_currency ?? "USD"}
          submitting={createMutation.isPending}
          onCancel={() => setDialog(null)}
          onSubmit={async (values) => {
            await createMutation.mutateAsync(values);
            setDialog(null);
          }}
        />
      </Modal>

      <Modal
        open={dialog?.type === "edit"}
        title="Edit account"
        description="Update the account name or archive it when you no longer need it."
        onClose={() => setDialog(null)}
      >
        {editingAccount ? (
          <AccountEditForm
            account={editingAccount}
            submitting={updateMutation.isPending}
            onCancel={() => setDialog(null)}
            onSubmit={async (values) => {
              await updateMutation.mutateAsync(values);
              setDialog(null);
            }}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={dialog?.type === "archive"}
        title="Archive account?"
        description={
          dialog?.type === "archive"
            ? `Archive “${dialog.account.name}”? Archived accounts stay in history but cannot receive new transactions.`
            : ""
        }
        confirmLabel="Archive account"
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
          void archiveMutation.mutateAsync(dialog.account.id).then(() => {
            setDialog(null);
          });
        }}
      />
    </PageContainer>
  );
}
