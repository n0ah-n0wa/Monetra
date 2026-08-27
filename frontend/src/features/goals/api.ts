import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export type Goal = {
  id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  currency: string;
  status: string;
};

export type GoalListParams = {
  page?: number;
  page_size?: number;
};

export async function fetchGoals(
  params: GoalListParams = {},
): Promise<PaginatedResponse<Goal>> {
  return apiClient.get<PaginatedResponse<Goal>>(`/goals${toSearchParams(params)}`);
}

export async function fetchGoal(id: string): Promise<Goal> {
  return apiClient.get<Goal>(`/goals/${id}`);
}
