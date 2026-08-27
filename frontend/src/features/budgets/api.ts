import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export type Budget = {
  id: string;
  name: string;
  amount: string;
  currency: string;
  period_type: string;
  status: string;
};

export type BudgetListParams = {
  page?: number;
  page_size?: number;
};

export async function fetchBudgets(
  params: BudgetListParams = {},
): Promise<PaginatedResponse<Budget>> {
  return apiClient.get<PaginatedResponse<Budget>>(`/budgets${toSearchParams(params)}`);
}

export async function fetchBudget(id: string): Promise<Budget> {
  return apiClient.get<Budget>(`/budgets/${id}`);
}
