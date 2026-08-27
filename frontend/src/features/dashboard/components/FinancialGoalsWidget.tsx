import { Link } from "react-router-dom";
import {
  FinancialProgressBar,
  FinancialProgressStats,
} from "@/components/financial/FinancialProgress";
import { DashboardWidget } from "@/features/dashboard/components/DashboardWidget";
import { formatGoalProjection } from "@/features/goals/api";
import { useGoalsQuery } from "@/features/goals/hooks";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

const DASHBOARD_GOALS_PARAMS = {
  page: 1,
  page_size: 5,
  include_progress: true,
  status: "active" as const,
};

export function FinancialGoalsWidget() {
  const query = useGoalsQuery(DASHBOARD_GOALS_PARAMS);

  return (
    <DashboardWidget
      title="Financial goals"
      description="Progress toward your savings targets."
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={query.isSuccess && query.data.items.length === 0}
      emptyTitle="No active goals"
      emptyDescription="Set a goal to track long-term savings targets."
      skeletonLines={4}
    >
      <div className="dashboard-list" role="list" aria-label="Financial goals">
        {query.data?.items.map((goal) => (
          <article key={goal.id} className="dashboard-goal" role="listitem">
            <div className="dashboard-goal__header">
              <Link className="dashboard-list__title" to={routes.goalDetail(goal.id)}>
                {goal.name}
              </Link>
              {goal.progress ? (
                <span className="dashboard-goal__percent">
                  {formatPercentDisplay(goal.progress.completion_percentage)}
                </span>
              ) : null}
            </div>
            {goal.progress ? (
              <>
                <FinancialProgressBar
                  percentage={goal.progress.completion_percentage}
                  label={`${goal.name} progress`}
                  variant="goal"
                />
                <FinancialProgressStats
                  stats={[
                    {
                      label: "Saved",
                      value: formatMoneyDisplay(goal.current_amount, goal.currency),
                    },
                    {
                      label: "Target",
                      value: formatMoneyDisplay(goal.target_amount, goal.currency),
                    },
                    {
                      label: "Remaining",
                      value: formatMoneyDisplay(
                        goal.progress.remaining_amount,
                        goal.currency,
                      ),
                    },
                  ]}
                />
              </>
            ) : (
              <p className="dashboard-list__meta">
                {formatMoneyDisplay(goal.current_amount, goal.currency)} of{" "}
                {formatMoneyDisplay(goal.target_amount, goal.currency)}
              </p>
            )}
            {goal.progress ? (
              <p className="dashboard-list__meta">
                Projection: {formatGoalProjection(goal)}
              </p>
            ) : null}
          </article>
        ))}
      </div>
      <p className="dashboard-widget__footer">
        <Link to={routes.goals}>View all goals</Link>
      </p>
    </DashboardWidget>
  );
}
