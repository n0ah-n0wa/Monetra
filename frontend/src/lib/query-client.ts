import { QueryClient } from "@tanstack/react-query";
import { isApiError } from "@/api/errors";

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (isApiError(error)) {
    if (error.status === 401 || error.status === 403 || error.status === 404) {
      return false;
    }
  }
  return failureCount < 1;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: shouldRetry,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export const queryKeys = {
  health: ["health"] as const,
  currentUser: ["users", "me"] as const,
  accounts: {
    all: ["accounts"] as const,
    list: (params?: Record<string, unknown>) => ["accounts", "list", params] as const,
    detail: (id: string) => ["accounts", "detail", id] as const,
  },
  transactions: {
    all: ["transactions"] as const,
    list: (params?: Record<string, unknown>) =>
      ["transactions", "list", params] as const,
    detail: (id: string) => ["transactions", "detail", id] as const,
  },
  recurringTransactions: {
    all: ["recurring-transactions"] as const,
    list: (params?: Record<string, unknown>) =>
      ["recurring-transactions", "list", params] as const,
    detail: (id: string) => ["recurring-transactions", "detail", id] as const,
  },
  imports: {
    all: ["imports"] as const,
    list: (params?: Record<string, unknown>) => ["imports", "list", params] as const,
    detail: (id: string) => ["imports", "detail", id] as const,
  },
  categories: {
    all: ["categories"] as const,
    list: (params?: Record<string, unknown>) => ["categories", "list", params] as const,
    detail: (id: string) => ["categories", "detail", id] as const,
  },
  budgets: {
    all: ["budgets"] as const,
    list: (params?: Record<string, unknown>) => ["budgets", "list", params] as const,
    detail: (id: string) => ["budgets", "detail", id] as const,
  },
  goals: {
    all: ["goals"] as const,
    list: (params?: Record<string, unknown>) => ["goals", "list", params] as const,
    detail: (id: string) => ["goals", "detail", id] as const,
  },
  transfers: {
    all: ["transfers"] as const,
    list: (params?: Record<string, unknown>) => ["transfers", "list", params] as const,
  },
  analytics: {
    root: ["analytics"] as const,
    incomeVsExpenses: (params?: Record<string, unknown>) =>
      ["analytics", "income-vs-expenses", params] as const,
    netCashFlow: (params?: Record<string, unknown>) =>
      ["analytics", "net-cash-flow", params] as const,
    balanceOverTime: (params?: Record<string, unknown>) =>
      ["analytics", "balance-over-time", params] as const,
    savingsRate: (params?: Record<string, unknown>) =>
      ["analytics", "savings-rate", params] as const,
    spendingByCategory: (params?: Record<string, unknown>) =>
      ["analytics", "spending-by-category", params] as const,
    periodComparison: (params?: Record<string, unknown>) =>
      ["analytics", "period-comparison", params] as const,
    largestExpenses: (params?: Record<string, unknown>) =>
      ["analytics", "largest-expenses", params] as const,
    budgetUtilization: (params?: Record<string, unknown>) =>
      ["analytics", "budget-utilization", params] as const,
  },
  notifications: {
    all: ["notifications"] as const,
    list: (params?: Record<string, unknown>) =>
      ["notifications", "list", params] as const,
    unreadCount: ["notifications", "unread-count"] as const,
    preferences: ["notifications", "preferences"] as const,
  },
  settings: {
    profile: ["settings", "profile"] as const,
  },
} as const;
