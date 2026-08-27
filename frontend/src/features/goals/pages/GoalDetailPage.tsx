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
  formatGoalProjection,
  formatGoalStatus,
  goalStatusVariant,
} from "@/features/goals/api";
import { GoalEditForm } from "@/features/goals/components/GoalForm";
import {
  useArchiveGoalMutation,
  useGoalQuery,
  useUpdateGoalMutation,
} from "@/features/goals/hooks";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

export function GoalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const goalQuery = useGoalQuery(id);
  const updateMutation = useUpdateGoalMutation();
  const archiveMutation = useArchiveGoalMutation();

  if (goalQuery.isPending) {
    return (
      <PageContainer>
        <LoadingState title="Loading goal" />
      </PageContainer>
    );
  }

  if (goalQuery.isError || !goalQuery.data) {
    return (
      <PageContainer>
        <ErrorState
          error={goalQuery.error}
          title="Unable to load goal"
          onRetry={() => void goalQuery.refetch()}
        />
        <p>
          <Link to={routes.goals}>Back to goals</Link>
        </p>
      </PageContainer>
    );
  }

  const goal = goalQuery.data;
  const isActive = goal.status === "active";
  const progress = goal.progress;

  return (
    <PageContainer>
      <PageHeader
        title={goal.name}
        description={`${goal.currency}${goal.target_date ? ` · Target date ${goal.target_date}` : ""}`}
        actions={
          <div className="page-header__actions">
            <Link className="btn btn--secondary btn--sm" to={routes.goals}>
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
            <CardTitle>Progress</CardTitle>
            <CardDescription>
              Status:{" "}
              <Badge variant={goalStatusVariant(goal.status)}>
                {formatGoalStatus(goal.status)}
              </Badge>
            </CardDescription>
          </CardHeader>
          <CardContent className="stack">
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
                      value: formatMoneyDisplay(goal.target_amount, goal.currency),
                    },
                    {
                      label: "Current",
                      value: formatMoneyDisplay(goal.current_amount, goal.currency),
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
              </>
            ) : (
              <p className="stat-value">
                {formatMoneyDisplay(goal.current_amount, goal.currency)} of{" "}
                {formatMoneyDisplay(goal.target_amount, goal.currency)}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Projection</CardTitle>
          </CardHeader>
          <CardContent className="stack">
            <p>{formatGoalProjection(goal)}</p>
            {progress?.required_average_contribution ? (
              <p>
                Required daily contribution:{" "}
                {formatMoneyDisplay(
                  progress.required_average_contribution,
                  goal.currency,
                )}
              </p>
            ) : null}
            {progress?.average_contribution_rate ? (
              <p>
                Average contribution rate:{" "}
                {formatMoneyDisplay(progress.average_contribution_rate, goal.currency)}{" "}
                per day
              </p>
            ) : null}
            {progress?.projected_completion_date ? (
              <p>Projected completion: {progress.projected_completion_date}</p>
            ) : null}
            {goal.target_date ? <p>Target date: {goal.target_date}</p> : null}
            {goal.archived_at ? <p>Archived at: {goal.archived_at}</p> : null}
          </CardContent>
        </Card>
      </div>

      <Modal open={editing} title="Edit goal" onClose={() => setEditing(false)}>
        <GoalEditForm
          goal={goal}
          submitting={updateMutation.isPending}
          onCancel={() => setEditing(false)}
          onSubmit={async (payload) => {
            await updateMutation.mutateAsync({ id: goal.id, payload });
            setEditing(false);
          }}
        />
      </Modal>

      <ConfirmDialog
        open={archiving}
        title="Archive goal?"
        description={`Archive “${goal.name}”? Archived goals stay in history but are no longer active.`}
        confirmLabel="Archive goal"
        loading={archiveMutation.isPending}
        error={archiveMutation.error}
        onCancel={() => {
          archiveMutation.reset();
          setArchiving(false);
        }}
        onConfirm={() => {
          void archiveMutation.mutateAsync(goal.id).then(() => {
            setArchiving(false);
            navigate(routes.goals, { replace: true });
          });
        }}
      />
    </PageContainer>
  );
}
