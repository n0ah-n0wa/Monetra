import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";
import type { TransactionType } from "@/features/transactions/api";

export const RECURRING_FREQUENCIES = [
  "daily",
  "weekly",
  "biweekly",
  "monthly",
  "quarterly",
  "yearly",
] as const;

export type RecurringFrequency = (typeof RECURRING_FREQUENCIES)[number];

export type RecurringTransaction = {
  id: string;
  account_id: string;
  category_id: string;
  transaction_type: TransactionType;
  amount: string;
  currency: string;
  description: string;
  frequency: RecurringFrequency;
  start_date: string;
  end_date: string | null;
  next_execution_date: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type RecurringTransactionListParams = {
  page?: number;
  page_size?: number;
  is_active?: boolean;
};

export type RecurringTransactionCreatePayload = {
  account_id: string;
  category_id: string;
  transaction_type: TransactionType;
  amount: string;
  description: string;
  frequency: RecurringFrequency;
  start_date: string;
  end_date?: string | null;
};

export type RecurringTransactionUpdatePayload = {
  account_id?: string;
  category_id?: string;
  transaction_type?: TransactionType;
  amount?: string;
  description?: string;
  frequency?: RecurringFrequency;
  start_date?: string;
  end_date?: string | null;
  is_active?: boolean;
};

export function formatRecurringFrequency(frequency: RecurringFrequency): string {
  const labels: Record<RecurringFrequency, string> = {
    daily: "Daily",
    weekly: "Weekly",
    biweekly: "Biweekly",
    monthly: "Monthly",
    quarterly: "Quarterly",
    yearly: "Yearly",
  };
  return labels[frequency];
}

export function recurringStatusLabel(isActive: boolean): string {
  return isActive ? "Active" : "Inactive";
}

export function recurringStatusVariant(isActive: boolean): "success" | "neutral" {
  return isActive ? "success" : "neutral";
}

export async function fetchRecurringTransactions(
  params: RecurringTransactionListParams = {},
): Promise<PaginatedResponse<RecurringTransaction>> {
  return apiClient.get<PaginatedResponse<RecurringTransaction>>(
    `/recurring-transactions${toSearchParams(params)}`,
  );
}

export async function fetchRecurringTransaction(
  id: string,
): Promise<RecurringTransaction> {
  return apiClient.get<RecurringTransaction>(`/recurring-transactions/${id}`);
}

export async function createRecurringTransaction(
  payload: RecurringTransactionCreatePayload,
): Promise<RecurringTransaction> {
  return apiClient.post<RecurringTransaction>("/recurring-transactions", payload);
}

export async function updateRecurringTransaction(
  id: string,
  payload: RecurringTransactionUpdatePayload,
): Promise<RecurringTransaction> {
  return apiClient.patch<RecurringTransaction>(
    `/recurring-transactions/${id}`,
    payload,
  );
}

export async function archiveRecurringTransaction(
  id: string,
): Promise<RecurringTransaction> {
  return apiClient.post<RecurringTransaction>(`/recurring-transactions/${id}/archive`);
}
