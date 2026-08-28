import type { APIRequestContext } from "@playwright/test";
import { API_PREFIX } from "./constants";
import { authHeaders, type TestUser } from "./auth";

export type AccountRef = {
  id: string;
  name: string;
  currency: string;
};

export async function createAccount(
  request: APIRequestContext,
  user: TestUser,
  name: string,
  options: {
    currency?: string;
    opening_balance?: string;
    account_type?: string;
  } = {},
): Promise<AccountRef> {
  const response = await request.post(`${API_PREFIX}/accounts`, {
    headers: authHeaders(user.accessToken),
    data: {
      name,
      account_type: options.account_type ?? "bank",
      currency: options.currency ?? "USD",
      opening_balance: options.opening_balance ?? "5000.0000",
    },
  });
  if (!response.ok()) {
    throw new Error(`Create account failed: ${await response.text()}`);
  }
  const body = (await response.json()) as AccountRef & { id: string };
  return { id: body.id, name: body.name, currency: body.currency };
}

export async function createCategory(
  request: APIRequestContext,
  user: TestUser,
  name: string,
  category_type: "income" | "expense",
): Promise<{ id: string; name: string }> {
  const response = await request.post(`${API_PREFIX}/categories`, {
    headers: authHeaders(user.accessToken),
    data: { name, category_type },
  });
  if (!response.ok()) {
    throw new Error(`Create category failed: ${await response.text()}`);
  }
  const body = (await response.json()) as { id: string; name: string };
  return body;
}

export async function createTransaction(
  request: APIRequestContext,
  user: TestUser,
  payload: {
    account_id: string;
    category_id: string;
    transaction_type: "income" | "expense";
    amount: string;
    description: string;
    transaction_date?: string;
  },
): Promise<{ id: string; description: string }> {
  const response = await request.post(`${API_PREFIX}/transactions`, {
    headers: authHeaders(user.accessToken),
    data: {
      transaction_date: payload.transaction_date ?? "2026-02-01",
      ...payload,
    },
  });
  if (!response.ok()) {
    throw new Error(`Create transaction failed: ${await response.text()}`);
  }
  const body = (await response.json()) as { id: string; description: string };
  return body;
}

export async function createTransfer(
  request: APIRequestContext,
  user: TestUser,
  payload: {
    source_account_id: string;
    destination_account_id: string;
    source_amount: string;
    transaction_date?: string;
    description?: string;
  },
): Promise<{ id: string }> {
  const response = await request.post(`${API_PREFIX}/transfers`, {
    headers: authHeaders(user.accessToken),
    data: {
      transaction_date: payload.transaction_date ?? "2026-02-01",
      description: payload.description ?? "E2E transfer",
      ...payload,
    },
  });
  if (!response.ok()) {
    throw new Error(`Create transfer failed: ${await response.text()}`);
  }
  const body = (await response.json()) as { id: string };
  return body;
}

export async function fetchAccountBalance(
  request: APIRequestContext,
  user: TestUser,
  accountId: string,
): Promise<string> {
  const response = await request.get(`${API_PREFIX}/accounts/${accountId}`, {
    headers: authHeaders(user.accessToken),
  });
  if (!response.ok()) {
    throw new Error(`Fetch account failed: ${await response.text()}`);
  }
  const body = (await response.json()) as { current_balance: string };
  return body.current_balance;
}

export async function listCategories(
  request: APIRequestContext,
  user: TestUser,
): Promise<Array<{ id: string; name: string; category_type: string }>> {
  const response = await request.get(
    `${API_PREFIX}/categories?page=1&page_size=100&include_system=true`,
    { headers: authHeaders(user.accessToken) },
  );
  if (!response.ok()) {
    throw new Error(`List categories failed: ${await response.text()}`);
  }
  const body = (await response.json()) as {
    items: Array<{ id: string; name: string; category_type: string }>;
  };
  return body.items;
}

export async function exportTransactionsCsv(
  request: APIRequestContext,
  user: TestUser,
): Promise<string> {
  const response = await request.get(`${API_PREFIX}/exports/transactions`, {
    headers: {
      ...authHeaders(user.accessToken),
      Accept: "text/csv",
    },
  });
  if (!response.ok()) {
    throw new Error(`Export failed: ${await response.text()}`);
  }
  return response.text();
}

export function buildImportCsv(rows: Array<Record<string, string>>): string {
  const headers = [
    "transaction_date",
    "transaction_type",
    "amount",
    "description",
    "category",
  ];
  const lines = [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => row[header] ?? "").join(",")),
  ];
  return lines.join("\n");
}
