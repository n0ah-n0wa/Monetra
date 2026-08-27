import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export const BUDGET_PERIODS = ["weekly", "monthly", "yearly", "custom"] as const;
export type BudgetPeriod = (typeof BUDGET_PERIODS)[number];

export const BUDGET_SCOPES = ["overall", "category"] as const;
export type BudgetScope = (typeof BUDGET_SCOPES)[number];

export const BUDGET_UTILIZATION_STATUSES = ["healthy", "warning", "exceeded"] as const;
export type BudgetUtilizationStatus = (typeof BUDGET_UTILIZATION_STATUSES)[number];

export type BudgetCategorySummary = {
  id: string;
  name: string;
};

export type BudgetUtilization = {
  as_of_date: string;
  period_start: string;
  period_end: string;
  budget_amount: string;
  spent_amount: string;
  remaining_amount: string;
  percentage_used: string;
  status: BudgetUtilizationStatus;
};

export type Budget = {
  id: string;
  name: string;
  amount: string;
  currency: string;
  period: BudgetPeriod;
  scope: BudgetScope;
  start_date: string;
  end_date: string | null;
  warning_threshold_percent: number;
  categories: BudgetCategorySummary[];
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  utilization: BudgetUtilization | null;
};

export type BudgetListParams = {
  page?: number;
  page_size?: number;
  include_archived?: boolean;
  include_utilization?: boolean;
  as_of_date?: string;
};

export type BudgetCreatePayload = {
  name: string;
  amount: string;
  currency: string;
  period: BudgetPeriod;
  scope: BudgetScope;
  start_date: string;
  end_date?: string | null;
  warning_threshold_percent?: number;
  category_ids?: string[];
};

export type BudgetUpdatePayload = {
  name?: string;
  amount?: string;
  currency?: string;
  period?: BudgetPeriod;
  scope?: BudgetScope;
  start_date?: string;
  end_date?: string | null;
  warning_threshold_percent?: number;
  category_ids?: string[];
};

export function formatBudgetPeriod(period: BudgetPeriod): string {
  return period.charAt(0).toUpperCase() + period.slice(1);
}

export function formatBudgetScope(scope: BudgetScope): string {
  return scope === "overall" ? "Overall" : "Category";
}

export function budgetDisplayStatus(budget: Budget): string {
  if (budget.archived_at) {
    return "archived";
  }
  return budget.utilization?.status ?? "healthy";
}

export function budgetStatusVariant(
  status: string,
): "success" | "warning" | "neutral" | "info" {
  if (status === "exceeded" || status === "warning") {
    return "warning";
  }
  if (status === "healthy") {
    return "success";
  }
  if (status === "archived") {
    return "neutral";
  }
  return "info";
}

export async function fetchBudgets(
  params: BudgetListParams = {},
): Promise<PaginatedResponse<Budget>> {
  return apiClient.get<PaginatedResponse<Budget>>(`/budgets${toSearchParams(params)}`);
}

export async function fetchBudget(
  id: string,
  params: Pick<BudgetListParams, "include_utilization" | "as_of_date"> = {
    include_utilization: true,
  },
): Promise<Budget> {
  return apiClient.get<Budget>(`/budgets/${id}${toSearchParams(params)}`);
}

export async function createBudget(payload: BudgetCreatePayload): Promise<Budget> {
  return apiClient.post<Budget>("/budgets", payload);
}

export async function updateBudget(
  id: string,
  payload: BudgetUpdatePayload,
): Promise<Budget> {
  return apiClient.patch<Budget>(`/budgets/${id}`, payload);
}

export async function archiveBudget(id: string): Promise<Budget> {
  return apiClient.post<Budget>(`/budgets/${id}/archive`);
}
