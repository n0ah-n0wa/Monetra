import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";

export type Transfer = {
  id: string;
  source_account_id: string;
  destination_account_id: string;
  source_amount: string;
  source_currency: string;
  destination_amount: string;
  destination_currency: string;
  exchange_rate: string | null;
  transaction_date: string;
  description: string | null;
  idempotency_key: string | null;
  created_at: string;
  updated_at: string;
};

export type TransferCreatePayload = {
  source_account_id: string;
  destination_account_id: string;
  source_amount: string;
  destination_amount?: string;
  exchange_rate?: string;
  transaction_date: string;
  description?: string;
  idempotency_key?: string;
};

export type TransferListParams = {
  page?: number;
  page_size?: number;
};

export async function fetchTransfers(
  params: TransferListParams = {},
): Promise<PaginatedResponse<Transfer>> {
  const search = new URLSearchParams();
  if (params.page) {
    search.set("page", String(params.page));
  }
  if (params.page_size) {
    search.set("page_size", String(params.page_size));
  }
  const query = search.toString();
  return apiClient.get<PaginatedResponse<Transfer>>(
    `/transfers${query ? `?${query}` : ""}`,
  );
}

export async function createTransfer(
  payload: TransferCreatePayload,
): Promise<Transfer> {
  return apiClient.post<Transfer>("/transfers", payload);
}
