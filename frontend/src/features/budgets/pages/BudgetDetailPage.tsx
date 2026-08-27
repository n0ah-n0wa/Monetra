import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  FinancialProgressBar,
  FinancialProgressStats,
} from "@/components/financial/FinancialProgress";
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
import {
  budgetDisplayStatus,
  budgetStatusVariant,
  formatBudgetPeriod,
  formatBudgetScope,
} from "@/features/budgets/api";
import { BudgetEditForm } from "@/features/budgets/components/BudgetForm";
import {
  useArchiveBudgetMutation,
  useBudgetQuery,
  useUpdateBudgetMutation,
} from "@/features/budgets/hooks";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

export function BudgetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const budgetQuery = useBudgetQuery(id);
  const updateMutation = useUpdateBudgetMutation();
  const archiveMutation = useArchiveBudgetMutation();

  if (budgetQuery.isPending) {
    return (
      <PageContainer>
        <LoadingState title="Loading budget" />
      </PageContainer>
    );
  }

  if (budgetQuery.isError || !budgetQuery.data) {
    return (
      <PageContainer>
        <ErrorState
          error={budgetQuery.error}
          title="Unable to load budget"
          onRetry={() => void budgetQuery.refetch()}
        />
        <p>
          <Link to={routes.budgets}>Back to budgets</Link>
        </p>
      </PageContainer>
    );
  }

  const budget = budgetQuery.data;
  const isActive = !budget.archived_at;
  const status = budgetDisplayStatus(budget);
  const utilization = budget.utilization;

  return (
    <PageContainer>
      <PageHeader
        title={budget.name}
        description={`${formatBudgetPeriod(budget.period)} · ${formatBudgetScope(budget.scope)} · ${budget.currency}`}
        actions={
          <div className="page-header__actions">
            <Link className="btn btn--secondary btn--sm" to={routes.budgets}>
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
            <CardTitle>Utilization</CardTitle>
            <CardDescription>
              Status: <Badge variant={budgetStatusVariant(status)}>{status}</Badge>
            </CardDescription>
          </CardHeader>
          <CardContent className="stack">
            {utilization ? (
              <>
                <FinancialProgressBar
                  percentage={utilization.percentage_used}
                  label={`${budget.name} utilization`}
                  status={utilization.status}
                />
                <FinancialProgressStats
                  stats={[
                    {
                      label: "Amount",
                      value: formatMoneyDisplay(budget.amount, budget.currency),
                    },
                    {
                      label: "Spent",
                      value: formatMoneyDisplay(
                        utilization.spent_amount,
                        budget.currency,
                      ),
                    },
                    {
                      label: "Remaining",
                      value: formatMoneyDisplay(
                        utilization.remaining_amount,
                        budget.currency,
                      ),
                    },
                    {
                      label: "Used",
                      value: formatPercentDisplay(utilization.percentage_used),
                    },
                  ]}
                />
                <p className="data-card__meta">
                  Period: {utilization.period_start} to {utilization.period_end}
                </p>
              </>
            ) : (
              <p className="stat-value">
                {formatMoneyDisplay(budget.amount, budget.currency)}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="stack">
            <p>Start date: {budget.start_date}</p>
            {budget.end_date ? <p>End date: {budget.end_date}</p> : null}
            <p>Warning threshold: {budget.warning_threshold_percent}%</p>
            {budget.categories.length > 0 ? (
              <p>
                Categories:{" "}
                {budget.categories.map((category) => category.name).join(", ")}
              </p>
            ) : (
              <p>Scope: all expenses</p>
            )}
            {budget.archived_at ? <p>Archived at: {budget.archived_at}</p> : null}
          </CardContent>
        </Card>
      </div>

      <Modal open={editing} title="Edit budget" onClose={() => setEditing(false)}>
        <BudgetEditForm
          budget={budget}
          submitting={updateMutation.isPending}
          onCancel={() => setEditing(false)}
          onSubmit={async (payload) => {
            await updateMutation.mutateAsync({ id: budget.id, payload });
            setEditing(false);
          }}
        />
      </Modal>

      <ConfirmDialog
        open={archiving}
        title="Archive budget?"
        description={`Archive “${budget.name}”? Archived budgets stay in history but no longer track new spending.`}
        confirmLabel="Archive budget"
        loading={archiveMutation.isPending}
        error={archiveMutation.error}
        onCancel={() => {
          archiveMutation.reset();
          setArchiving(false);
        }}
        onConfirm={() => {
          void archiveMutation.mutateAsync(budget.id).then(() => {
            setArchiving(false);
            navigate(routes.budgets, { replace: true });
          });
        }}
      />
    </PageContainer>
  );
}
