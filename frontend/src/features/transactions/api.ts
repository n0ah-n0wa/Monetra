import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export const TRANSACTION_TYPES = ["income", "expense"] as const;
export type TransactionType = (typeof TRANSACTION_TYPES)[number];

export const TRANSACTION_SORT_FIELDS = [
  "transaction_date",
  "amount",
  "created_at",
  "description",
] as const;
export type TransactionSortField = (typeof TRANSACTION_SORT_FIELDS)[number];

export const SORT_ORDERS = ["asc", "desc"] as const;
export type SortOrder = (typeof SORT_ORDERS)[number];

export type Transaction = {
  id: string;
  account_id: string;
  category_id: string;
  transaction_type: TransactionType;
  amount: string;
  currency: string;
  description: string;
  transaction_date: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type TransactionListParams = {
  page?: number;
  page_size?: number;
  account_id?: string;
  category_id?: string;
  transaction_type?: TransactionType;
  date_from?: string;
  date_to?: string;
  amount_min?: string;
  amount_max?: string;
  currency?: string;
  description?: string;
  sort_by?: TransactionSortField;
  sort_order?: SortOrder;
};

export type TransactionCreatePayload = {
  account_id: string;
  category_id: string;
  transaction_type: TransactionType;
  amount: string;
  description: string;
  transaction_date: string;
  notes?: string | null;
};

export type TransactionUpdatePayload = {
  account_id?: string;
  category_id?: string;
  transaction_type?: TransactionType;
  amount?: string;
  description?: string;
  transaction_date?: string;
  notes?: string | null;
};

export async function fetchTransactions(
  params: TransactionListParams = {},
): Promise<PaginatedResponse<Transaction>> {
  return apiClient.get<PaginatedResponse<Transaction>>(
    `/transactions${toSearchParams(params)}`,
  );
}

export async function fetchTransaction(id: string): Promise<Transaction> {
  return apiClient.get<Transaction>(`/transactions/${id}`);
}

export async function createTransaction(
  payload: TransactionCreatePayload,
): Promise<Transaction> {
  return apiClient.post<Transaction>("/transactions", payload);
}

export async function updateTransaction(
  id: string,
  payload: TransactionUpdatePayload,
): Promise<Transaction> {
  return apiClient.patch<Transaction>(`/transactions/${id}`, payload);
}

export async function deleteTransaction(id: string): Promise<void> {
  await apiClient.delete(`/transactions/${id}`);
}

export function formatTransactionType(type: TransactionType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

export function formatSortField(field: TransactionSortField): string {
  switch (field) {
    case "transaction_date":
      return "Date";
    case "amount":
      return "Amount";
    case "created_at":
      return "Created";
    case "description":
      return "Description";
    default:
      return field;
  }
}
