import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export type Transaction = {
  id: string;
  account_id: string;
  category_id: string | null;
  amount: string;
  currency: string;
  transaction_type: string;
  transaction_date: string;
  payee: string | null;
  notes: string | null;
};

export type TransactionListParams = {
  page?: number;
  page_size?: number;
  account_id?: string;
};

export async function fetchTransactions(
  params: TransactionListParams = {},
): Promise<PaginatedResponse<Transaction>> {
  return apiClient.get<PaginatedResponse<Transaction>>(`/transactions${toSearchParams(params)}`);
}

export async function fetchTransaction(id: string): Promise<Transaction> {
  return apiClient.get<Transaction>(`/transactions/${id}`);
}
