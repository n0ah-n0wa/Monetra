import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";
import { formatMoneyDisplay } from "@/lib/money";

export const GOAL_STATUSES = ["active", "completed", "archived"] as const;
export type GoalStatus = (typeof GOAL_STATUSES)[number];

export type GoalProgress = {
  as_of_date: string;
  remaining_amount: string;
  completion_percentage: string;
  required_average_contribution: string | null;
  average_contribution_rate: string | null;
  projected_completion_date: string | null;
  target_date_achievable: boolean | null;
};

export type Goal = {
  id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  currency: string;
  target_date: string | null;
  linked_account_id: string | null;
  status: GoalStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  progress: GoalProgress | null;
};

export type GoalListParams = {
  page?: number;
  page_size?: number;
  status?: GoalStatus;
  include_archived?: boolean;
  include_progress?: boolean;
  as_of_date?: string;
};

export type GoalCreatePayload = {
  name: string;
  target_amount: string;
  current_amount?: string;
  currency: string;
  target_date?: string | null;
  linked_account_id?: string | null;
};

export type GoalUpdatePayload = {
  name?: string;
  target_amount?: string;
  current_amount?: string;
  currency?: string;
  target_date?: string | null;
  linked_account_id?: string | null;
};

export function formatGoalStatus(status: GoalStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function goalStatusVariant(
  status: GoalStatus,
): "success" | "warning" | "neutral" {
  if (status === "completed") {
    return "success";
  }
  if (status === "archived") {
    return "neutral";
  }
  return "warning";
}

export function formatGoalProjection(goal: Goal): string {
  if (goal.status === "completed") {
    return "Goal completed";
  }

  const progress = goal.progress;
  if (!progress) {
    return "—";
  }

  if (progress.projected_completion_date) {
    if (goal.target_date && progress.target_date_achievable === false) {
      return `Projected ${progress.projected_completion_date} (after target date)`;
    }
    if (goal.target_date && progress.target_date_achievable === true) {
      return `On track for ${goal.target_date}`;
    }
    return `Projected completion ${progress.projected_completion_date}`;
  }

  if (progress.required_average_contribution) {
    return `Requires ${formatMoneyDisplay(
      progress.required_average_contribution,
      goal.currency,
    )} per day`;
  }

  return "Insufficient data for projection";
}

export async function fetchGoals(
  params: GoalListParams = {},
): Promise<PaginatedResponse<Goal>> {
  return apiClient.get<PaginatedResponse<Goal>>(`/goals${toSearchParams(params)}`);
}

export async function fetchGoal(
  id: string,
  params: Pick<GoalListParams, "include_progress" | "as_of_date"> = {
    include_progress: true,
  },
): Promise<Goal> {
  return apiClient.get<Goal>(`/goals/${id}${toSearchParams(params)}`);
}

export async function createGoal(payload: GoalCreatePayload): Promise<Goal> {
  return apiClient.post<Goal>("/goals", payload);
}

export async function updateGoal(
  id: string,
  payload: GoalUpdatePayload,
): Promise<Goal> {
  return apiClient.patch<Goal>(`/goals/${id}`, payload);
}

export async function archiveGoal(id: string): Promise<Goal> {
  return apiClient.post<Goal>(`/goals/${id}/archive`);
}
