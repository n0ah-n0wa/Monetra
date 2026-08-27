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
import { useAuth } from "@/features/auth/hooks";
import {
  formatGoalProjection,
  formatGoalStatus,
  goalStatusVariant,
  type Goal,
  type GoalStatus,
} from "@/features/goals/api";
import { GoalCreateForm, GoalEditForm } from "@/features/goals/components/GoalForm";
import {
  useArchiveGoalMutation,
  useCreateGoalMutation,
  useGoalsQuery,
  useUpdateGoalMutation,
} from "@/features/goals/hooks";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

type DialogState =
  | { type: "create" }
  | { type: "edit"; goal: Goal }
  | { type: "archive"; goal: Goal }
  | null;

export function GoalsPage() {
  const { user } = useAuth();
  const [statusFilter, setStatusFilter] = useState<GoalStatus | "all">("active");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [dialog, setDialog] = useState<DialogState>(null);

  const listParams = useMemo(
    () => ({
      page: 1,
      page_size: 100,
      include_progress: true,
      status: statusFilter === "all" ? undefined : statusFilter,
      include_archived: includeArchived || statusFilter === "archived",
    }),
    [statusFilter, includeArchived],
  );

  const goalsQuery = useGoalsQuery(listParams);
  const createMutation = useCreateGoalMutation();
  const archiveMutation = useArchiveGoalMutation();

  const editingGoal = dialog?.type === "edit" ? dialog.goal : null;
  const updateMutation = useUpdateGoalMutation();

  return (
    <PageContainer>
      <PageHeader
        title="Goals"
        description="Track savings targets and milestone progress."
        actions={
          <Button onClick={() => setDialog({ type: "create" })}>Add goal</Button>
        }
      />

      <div className="toolbar">
        <label className="toolbar__filter" htmlFor="goal-status-filter">
          <span>Status</span>
          <Select
            id="goal-status-filter"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value as GoalStatus | "all")
            }
          >
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </Select>
        </label>
        {statusFilter !== "archived" ? (
          <label className="toolbar__filter" htmlFor="goal-archived-filter">
            <span>Include archived</span>
            <Select
              id="goal-archived-filter"
              value={includeArchived ? "yes" : "no"}
              onChange={(event) => setIncludeArchived(event.target.value === "yes")}
            >
              <option value="no">No</option>
              <option value="yes">Yes</option>
            </Select>
          </label>
        ) : null}
      </div>

      {goalsQuery.isPending ? <LoadingState title="Loading goals" /> : null}
      {goalsQuery.isError ? (
        <ErrorState
          error={goalsQuery.error}
          title="Unable to load goals"
          onRetry={() => void goalsQuery.refetch()}
        />
      ) : null}

      {goalsQuery.isSuccess && goalsQuery.data.items.length === 0 ? (
        <EmptyState
          title="No goals yet"
          description="Create a savings goal to track long-term targets."
        />
      ) : null}

      {goalsQuery.isSuccess && goalsQuery.data.items.length > 0 ? (
        <div className="data-list" role="list">
          {goalsQuery.data.items.map((goal) => {
            const progress = goal.progress;
            const isActive = goal.status === "active";

            return (
              <article key={goal.id} className="data-card" role="listitem">
                <div className="data-card__main">
                  <div className="data-card__title-row">
                    <Link className="data-card__title" to={routes.goalDetail(goal.id)}>
                      {goal.name}
                    </Link>
                    <Badge variant={goalStatusVariant(goal.status)}>
                      {formatGoalStatus(goal.status)}
                    </Badge>
                  </div>
                  <p className="data-card__meta">
                    {goal.currency}
                    {goal.target_date ? ` · Target date ${goal.target_date}` : null}
                  </p>
                  {progress ? (
                    <>
                      <FinancialProgressBar
                        percentage={progress.completion_percentage}
                        label={`${goal.name} progress`}
                        variant="goal"
                      />
                      <FinancialProgressStats
                        stats={[
                          {
                            label: "Target",
                            value: formatMoneyDisplay(
                              goal.target_amount,
                              goal.currency,
                            ),
                          },
                          {
                            label: "Current",
                            value: formatMoneyDisplay(
                              goal.current_amount,
                              goal.currency,
                            ),
                          },
                          {
                            label: "Remaining",
                            value: formatMoneyDisplay(
                              progress.remaining_amount,
                              goal.currency,
                            ),
                          },
                          {
                            label: "Complete",
                            value: formatPercentDisplay(progress.completion_percentage),
                          },
                        ]}
                      />
                      <p className="data-card__meta">
                        Projection: {formatGoalProjection(goal)}
                      </p>
                    </>
                  ) : (
                    <p className="data-card__value">
                      {formatMoneyDisplay(goal.current_amount, goal.currency)} of{" "}
                      {formatMoneyDisplay(goal.target_amount, goal.currency)}
                    </p>
                  )}
                </div>
                <div className="data-card__actions">
                  {isActive ? (
                    <>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setDialog({ type: "edit", goal })}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => setDialog({ type: "archive", goal })}
                      >
                        Archive
                      </Button>
                    </>
                  ) : (
                    <Link
                      className="btn btn--secondary btn--sm"
                      to={routes.goalDetail(goal.id)}
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
        title="Create goal"
        description="Set a savings target and optional deadline."
        onClose={() => setDialog(null)}
      >
        <GoalCreateForm
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
        title="Edit goal"
        onClose={() => setDialog(null)}
      >
        {editingGoal ? (
          <GoalEditForm
            goal={editingGoal}
            submitting={updateMutation.isPending}
            onCancel={() => setDialog(null)}
            onSubmit={async (payload) => {
              await updateMutation.mutateAsync({
                id: editingGoal.id,
                payload,
              });
              setDialog(null);
            }}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={dialog?.type === "archive"}
        title="Archive goal?"
        description={
          dialog?.type === "archive"
            ? `Archive “${dialog.goal.name}”? Archived goals stay in history but are no longer active.`
            : ""
        }
        confirmLabel="Archive goal"
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
          void archiveMutation.mutateAsync(dialog.goal.id).then(() => {
            setDialog(null);
          });
        }}
      />
    </PageContainer>
  );
}
