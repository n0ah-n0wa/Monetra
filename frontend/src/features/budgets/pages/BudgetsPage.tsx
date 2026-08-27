import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  FinancialProgressBar,
  FinancialProgressStats,
} from "@/components/financial/FinancialProgress";
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
  budgetDisplayStatus,
  budgetStatusVariant,
  formatBudgetPeriod,
  formatBudgetScope,
  type Budget,
} from "@/features/budgets/api";
import {
  BudgetCreateForm,
  BudgetEditForm,
} from "@/features/budgets/components/BudgetForm";
import {
  useArchiveBudgetMutation,
  useBudgetsQuery,
  useCreateBudgetMutation,
  useUpdateBudgetMutation,
} from "@/features/budgets/hooks";
import { useAuth } from "@/features/auth/hooks";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

type DialogState =
  | { type: "create" }
  | { type: "edit"; budget: Budget }
  | { type: "archive"; budget: Budget }
  | null;

export function BudgetsPage() {
  const { user } = useAuth();
  const [includeArchived, setIncludeArchived] = useState(false);
  const [dialog, setDialog] = useState<DialogState>(null);

  const listParams = useMemo(
    () => ({
      page: 1,
      page_size: 100,
      include_utilization: true,
      include_archived: includeArchived,
    }),
    [includeArchived],
  );

  const budgetsQuery = useBudgetsQuery(listParams);
  const createMutation = useCreateBudgetMutation();
  const archiveMutation = useArchiveBudgetMutation();

  const editingBudget = dialog?.type === "edit" ? dialog.budget : null;
  const updateMutation = useUpdateBudgetMutation();

  return (
    <PageContainer>
      <PageHeader
        title="Budgets"
        description="Set spending limits and monitor utilization over time."
        actions={
          <Button onClick={() => setDialog({ type: "create" })}>Add budget</Button>
        }
      />

      <div className="toolbar">
        <label className="toolbar__filter" htmlFor="budget-archived-filter">
          <span>Show archived</span>
          <Select
            id="budget-archived-filter"
            value={includeArchived ? "yes" : "no"}
            onChange={(event) => setIncludeArchived(event.target.value === "yes")}
          >
            <option value="no">Active only</option>
            <option value="yes">Include archived</option>
          </Select>
        </label>
      </div>

      {budgetsQuery.isPending ? <LoadingState title="Loading budgets" /> : null}
      {budgetsQuery.isError ? (
        <ErrorState
          error={budgetsQuery.error}
          title="Unable to load budgets"
          onRetry={() => void budgetsQuery.refetch()}
        />
      ) : null}

      {budgetsQuery.isSuccess && budgetsQuery.data.items.length === 0 ? (
        <EmptyState
          title="No budgets yet"
          description="Create a budget to track spending targets."
        />
      ) : null}

      {budgetsQuery.isSuccess && budgetsQuery.data.items.length > 0 ? (
        <div className="data-list" role="list">
          {budgetsQuery.data.items.map((budget) => {
            const status = budgetDisplayStatus(budget);
            const utilization = budget.utilization;
            const isActive = !budget.archived_at;

            return (
              <article key={budget.id} className="data-card" role="listitem">
                <div className="data-card__main">
                  <div className="data-card__title-row">
                    <Link
                      className="data-card__title"
                      to={routes.budgetDetail(budget.id)}
                    >
                      {budget.name}
                    </Link>
                    <Badge variant={budgetStatusVariant(status)}>{status}</Badge>
                  </div>
                  <p className="data-card__meta">
                    {formatBudgetPeriod(budget.period)} ·{" "}
                    {formatBudgetScope(budget.scope)} · {budget.currency}
                  </p>
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
                    </>
                  ) : (
                    <p className="data-card__value">
                      {formatMoneyDisplay(budget.amount, budget.currency)}
                    </p>
                  )}
                </div>
                <div className="data-card__actions">
                  {isActive ? (
                    <>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setDialog({ type: "edit", budget })}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => setDialog({ type: "archive", budget })}
                      >
                        Archive
                      </Button>
                    </>
                  ) : (
                    <Link
                      className="btn btn--secondary btn--sm"
                      to={routes.budgetDetail(budget.id)}
                    >
                      View
                    </Link>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}

      <Modal
        open={dialog?.type === "create"}
        title="Create budget"
        description="Define a spending limit for a period and scope."
        onClose={() => setDialog(null)}
      >
        <BudgetCreateForm
          defaultCurrency={user?.reporting_currency ?? "USD"}
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
        title="Edit budget"
        onClose={() => setDialog(null)}
      >
        {editingBudget ? (
          <BudgetEditForm
            budget={editingBudget}
            submitting={updateMutation.isPending}
            onCancel={() => setDialog(null)}
            onSubmit={async (payload) => {
              await updateMutation.mutateAsync({
                id: editingBudget.id,
                payload,
              });
              setDialog(null);
            }}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={dialog?.type === "archive"}
        title="Archive budget?"
        description={
          dialog?.type === "archive"
            ? `Archive “${dialog.budget.name}”? Archived budgets stay in history but no longer track new spending.`
            : ""
        }
        confirmLabel="Archive budget"
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
          void archiveMutation.mutateAsync(dialog.budget.id).then(() => {
            setDialog(null);
          });
        }}
      />
    </PageContainer>
  );
}
