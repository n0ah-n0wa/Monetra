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
import { AccountEditForm } from "@/features/accounts/components/AccountForm";
import { formatAccountType } from "@/features/accounts/api";
import {
  useAccountQuery,
  useArchiveAccountMutation,
  useUpdateAccountMutation,
} from "@/features/accounts/hooks";
import { formatMoneyDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

export function AccountDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const accountQuery = useAccountQuery(id);
  const updateMutation = useUpdateAccountMutation(id ?? "");
  const archiveMutation = useArchiveAccountMutation();

  if (accountQuery.isPending) {
    return (
      <PageContainer>
        <LoadingState title="Loading account" />
      </PageContainer>
    );
  }

  if (accountQuery.isError || !accountQuery.data) {
    return (
      <PageContainer>
        <ErrorState
          error={accountQuery.error}
          title="Unable to load account"
          onRetry={() => void accountQuery.refetch()}
        />
        <p>
          <Link to={routes.accounts}>Back to accounts</Link>
        </p>
      </PageContainer>
    );
  }

  const account = accountQuery.data;
  const isActive = account.status === "active";

  return (
    <PageContainer>
      <PageHeader
        title={account.name}
        description={`${formatAccountType(account.account_type)} · ${account.currency}`}
        actions={
          <div className="page-header__actions">
            <Link className="btn btn--secondary btn--sm" to={routes.accounts}>
              Back
            </Link>
            {isActive ? (
              <>
                <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
                  Edit
                </Button>
                <Button size="sm" variant="danger" onClick={() => setArchiving(true)}>
                  Archive
                </Button>
              </>
            ) : null}
          </div>
        }
      />

      <div className="dashboard-grid">
        <Card>
          <CardHeader>
            <CardTitle>Balance</CardTitle>
            <CardDescription>Current derived balance</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="stat-value">
              {formatMoneyDisplay(account.current_balance, account.currency)}
            </p>
            <p className="data-card__meta">
              Opening: {formatMoneyDisplay(account.opening_balance, account.currency)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="stack">
            <p>
              Status:{" "}
              <Badge variant={isActive ? "success" : "neutral"}>{account.status}</Badge>
            </p>
            <p>Type: {formatAccountType(account.account_type)}</p>
            <p>Currency: {account.currency}</p>
            {account.archived_at ? <p>Archived at: {account.archived_at}</p> : null}
          </CardContent>
        </Card>
      </div>

      <Modal open={editing} title="Edit account" onClose={() => setEditing(false)}>
        <AccountEditForm
          account={account}
          submitting={updateMutation.isPending}
          onCancel={() => setEditing(false)}
          onSubmit={async (values) => {
            await updateMutation.mutateAsync(values);
            setEditing(false);
          }}
        />
      </Modal>

      <ConfirmDialog
        open={archiving}
        title="Archive account?"
        description={`Archive “${account.name}”? You can still view history, but new activity will be blocked.`}
        confirmLabel="Archive account"
        loading={archiveMutation.isPending}
        error={archiveMutation.error}
        onCancel={() => {
          archiveMutation.reset();
          setArchiving(false);
        }}
        onConfirm={() => {
          void archiveMutation.mutateAsync(account.id).then(() => {
            setArchiving(false);
            navigate(routes.accounts, { replace: true });
          });
        }}
      />
    </PageContainer>
  );
}
