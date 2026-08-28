export const E2E_PASSWORD = "Password1!";
export const API_PREFIX = "/api/v1";

export function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export const routes = {
  login: "/login",
  register: "/register",
  dashboard: "/dashboard",
  accounts: "/accounts",
  categories: "/categories",
  transactions: "/transactions",
  transactionNew: "/transactions/new",
  budgets: "/budgets",
  goals: "/goals",
  analytics: "/analytics",
  import: "/import",
  notifications: "/notifications",
} as const;
