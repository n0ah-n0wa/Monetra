import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export type Account = {
  id: string;
  name: string;
  account_type: string;
  currency: string;
  opening_balance: string;
  current_balance: string;
  status: string;
  archived_at: string | null;
};

export type AccountListParams = {
  page?: number;
  page_size?: number;
  status?: string;
};

export async function fetchAccounts(
  params: AccountListParams = {},
): Promise<PaginatedResponse<Account>> {
  return apiClient.get<PaginatedResponse<Account>>(
    `/accounts${toSearchParams(params)}`,
  );
}

export async function fetchAccount(id: string): Promise<Account> {
  return apiClient.get<Account>(`/accounts/${id}`);
}
