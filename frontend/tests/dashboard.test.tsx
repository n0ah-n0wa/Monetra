import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as analyticsApi from "@/features/analytics/api";
import * as goalsApi from "@/features/goals/api";
import * as transactionsApi from "@/features/transactions/api";
import { DashboardPage } from "@/pages/DashboardPage";
import { routes } from "@/lib/routes";
import { renderWithAuth } from "./test-utils";

vi.mock("@/features/auth/api", () => ({
  refreshSession: vi.fn(async () => ({
    access_token: "token",
    token_type: "bearer",
    expires_in: 900,
  })),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  fetchCurrentUser: vi.fn(async () => ({
    id: "user-1",
    email: "user@example.com",
    reporting_currency: "USD",
  })),
  requestPasswordReset: vi.fn(),
  confirmPasswordReset: vi.fn(),
}));

vi.mock("@/features/analytics/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/analytics/api")>(
    "@/features/analytics/api",
  );
  return {
    ...actual,
    fetchBalanceOverTime: vi.fn(),
    fetchIncomeVsExpenses: vi.fn(),
    fetchNetCashFlow: vi.fn(),
    fetchSavingsRate: vi.fn(),
    fetchSpendingByCategory: vi.fn(),
    fetchPeriodComparison: vi.fn(),
    fetchLargestExpenses: vi.fn(),
    fetchBudgetUtilizationAnalytics: vi.fn(),
  };
});

vi.mock("@/features/transactions/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/transactions/api")>(
    "@/features/transactions/api",
  );
  return {
    ...actual,
    fetchTransactions: vi.fn(),
  };
});

vi.mock("@/features/goals/api", async () => {
  const actual =
    await vi.importActual<typeof import("@/features/goals/api")>(
      "@/features/goals/api",
    );
  return { ...actual, fetchGoals: vi.fn() };
});

const period = {
  preset: "current_month" as const,
  start_date: "2026-02-01",
  end_date: "2026-02-28",
  as_of_date: "2026-02-15",
};

function mockDashboardData() {
  vi.mocked(analyticsApi.fetchBalanceOverTime).mockResolvedValue({
    period,
    reporting_currency: "USD",
    opening_balance: "1000.0000",
    closing_balance: "2500.0000",
    points: [],
  });
  vi.mocked(analyticsApi.fetchIncomeVsExpenses).mockResolvedValue({
    period,
    reporting_currency: "USD",
    income: "3000.0000",
    expenses: "500.0000",
  });
  vi.mocked(analyticsApi.fetchNetCashFlow).mockResolvedValue({
    period,
    reporting_currency: "USD",
    granularity: "day",
    total_net_cash_flow: "1500.0000",
    points: [],
  });
  vi.mocked(analyticsApi.fetchSavingsRate).mockResolvedValue({
    period,
    reporting_currency: "USD",
    income: "3000.0000",
    expenses: "500.0000",
    net_cash_flow: "2500.0000",
    savings_rate_percent: "83.3333",
  });
  vi.mocked(analyticsApi.fetchSpendingByCategory).mockResolvedValue({
    period,
    reporting_currency: "USD",
    total_expenses: "500.0000",
    items: [
      {
        category_id: "cat-1",
        category_name: "Groceries",
        amount: "300.0000",
        percentage: "60.0000",
      },
    ],
  });
  vi.mocked(analyticsApi.fetchPeriodComparison).mockResolvedValue({
    current_period: period,
    previous_period: { ...period, preset: "previous_month", start_date: "2026-01-01" },
    reporting_currency: "USD",
    income: {
      current: "3000.0000",
      previous: "2800.0000",
      change: "200.0000",
      change_percent: "7.1429",
    },
    expenses: {
      current: "500.0000",
      previous: "600.0000",
      change: "-100.0000",
      change_percent: "-16.6667",
    },
    net_cash_flow: {
      current: "2500.0000",
      previous: "2200.0000",
      change: "300.0000",
      change_percent: "13.6364",
    },
    savings_rate_percent: null,
  });
  vi.mocked(analyticsApi.fetchLargestExpenses).mockResolvedValue({
    period,
    reporting_currency: "USD",
    items: [
      {
        transaction_id: "txn-1",
        description: "Rent",
        amount: "1200.0000",
        currency: "USD",
        reporting_amount: "1200.0000",
        transaction_date: "2026-02-01",
        category_name: "Housing",
        account_name: "Checking",
      },
    ],
  });
  vi.mocked(analyticsApi.fetchBudgetUtilizationAnalytics).mockResolvedValue({
    period,
    as_of_date: "2026-02-15",
    items: [],
  });
  vi.mocked(transactionsApi.fetchTransactions).mockResolvedValue({
    items: [
      {
        id: "txn-2",
        account_id: "acc-1",
        category_id: "cat-1",
        transaction_type: "expense",
        amount: "25.0000",
        currency: "USD",
        description: "Coffee shop",
        transaction_date: "2026-02-10",
        notes: null,
        created_at: "2026-02-10T00:00:00Z",
        updated_at: "2026-02-10T00:00:00Z",
      },
    ],
    page: 1,
    page_size: 5,
    total_items: 1,
    total_pages: 1,
  });
  vi.mocked(goalsApi.fetchGoals).mockResolvedValue({
    items: [],
    page: 1,
    page_size: 5,
    total_items: 0,
    total_pages: 0,
  });
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDashboardData();
  });

  it("renders summary stats from analytics endpoints", async () => {
    renderWithAuth(<DashboardPage />, {
      authenticated: true,
      initialEntries: [routes.dashboard],
      routes: [{ path: routes.dashboard, element: <DashboardPage /> }],
    });

    expect(await screen.findByText("Total balance")).toBeInTheDocument();
    expect(screen.getByText("$2,500.00")).toBeInTheDocument();
    expect(screen.getByText("Monthly income")).toBeInTheDocument();
    expect(screen.getByText("$3,000.00")).toBeInTheDocument();
    expect(screen.getByText("$1,500.00")).toBeInTheDocument();
    expect(screen.getByText("83.3333%")).toBeInTheDocument();
  });

  it("shows recent transactions and accessible category table", async () => {
    renderWithAuth(<DashboardPage />, {
      authenticated: true,
      initialEntries: [routes.dashboard],
      routes: [{ path: routes.dashboard, element: <DashboardPage /> }],
    });

    expect(await screen.findByText("Coffee shop")).toBeInTheDocument();
    const table = screen.getByRole("table", { name: /spending by category/i });
    expect(within(table).getByText("Groceries")).toBeInTheDocument();
    expect(within(table).getByText("$300.00")).toBeInTheDocument();
  });

  it("shows widget error state with retry", async () => {
    const user = userEvent.setup();
    vi.mocked(analyticsApi.fetchBalanceOverTime).mockRejectedValue(
      new Error("balance failed"),
    );

    renderWithAuth(<DashboardPage />, {
      authenticated: true,
      initialEntries: [routes.dashboard],
      routes: [{ path: routes.dashboard, element: <DashboardPage /> }],
    });

    const retryButtons = await screen.findAllByRole("button", { name: /try again/i });
    await user.click(retryButtons[0]);

    await waitFor(() => {
      expect(analyticsApi.fetchBalanceOverTime).toHaveBeenCalledTimes(2);
    });
  });

  it("shows empty states for budgets and goals", async () => {
    renderWithAuth(<DashboardPage />, {
      authenticated: true,
      initialEntries: [routes.dashboard],
      routes: [{ path: routes.dashboard, element: <DashboardPage /> }],
    });

    expect(await screen.findByText("No budgets configured")).toBeInTheDocument();
    expect(screen.getByText("No active goals")).toBeInTheDocument();
  });
});
