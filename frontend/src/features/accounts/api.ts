import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export const ACCOUNT_TYPES = [
  "cash",
  "bank",
  "savings",
  "credit_card",
  "digital_wallet",
] as const;

export type AccountType = (typeof ACCOUNT_TYPES)[number];
export type AccountStatus = "active" | "archived";

export type Account = {
  id: string;
  name: string;
  account_type: AccountType;
  currency: string;
  opening_balance: string;
  current_balance: string;
  status: AccountStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AccountListParams = {
  page?: number;
  page_size?: number;
  status?: AccountStatus;
};

export type AccountCreatePayload = {
  name: string;
  account_type: AccountType;
  currency: string;
  opening_balance: string;
};

export type AccountUpdatePayload = {
  name?: string;
  account_type?: AccountType;
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

export async function createAccount(payload: AccountCreatePayload): Promise<Account> {
  return apiClient.post<Account>("/accounts", payload);
}

export async function updateAccount(
  id: string,
  payload: AccountUpdatePayload,
): Promise<Account> {
  return apiClient.patch<Account>(`/accounts/${id}`, payload);
}

export async function archiveAccount(id: string): Promise<Account> {
  return apiClient.post<Account>(`/accounts/${id}/archive`);
}

export function formatAccountType(type: AccountType): string {
  return type
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
