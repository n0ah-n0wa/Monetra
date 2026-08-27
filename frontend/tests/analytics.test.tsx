import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as analyticsApi from "@/features/analytics/api";
import { AnalyticsPage } from "@/features/analytics/pages/AnalyticsPage";
import { routes } from "@/lib/routes";
import { renderWithAuth } from "./test-utils";

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => (
      <div style={{ width: 800, height: 400 }}>{children}</div>
    ),
  };
});

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
    fetchIncomeVsExpenses: vi.fn(),
    fetchSpendingByCategory: vi.fn(),
    fetchBalanceOverTime: vi.fn(),
    fetchNetCashFlow: vi.fn(),
    fetchBudgetUtilizationAnalytics: vi.fn(),
    fetchPeriodComparison: vi.fn(),
  };
});

const period = {
  preset: "last_30_days" as const,
  start_date: "2026-01-28",
  end_date: "2026-02-27",
  as_of_date: "2026-02-27",
};

function mockAnalyticsSuccess() {
  vi.mocked(analyticsApi.fetchIncomeVsExpenses).mockResolvedValue({
    period,
    reporting_currency: "USD",
    income: "3000.0000",
    expenses: "500.0000",
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
  vi.mocked(analyticsApi.fetchBalanceOverTime).mockResolvedValue({
    period,
    reporting_currency: "USD",
    opening_balance: "1000.0000",
    closing_balance: "2500.0000",
    points: [{ bucket_date: "2026-02-01", balance: "1500.0000" }],
  });
  vi.mocked(analyticsApi.fetchNetCashFlow).mockResolvedValue({
    period,
    reporting_currency: "USD",
    granularity: "day",
    total_net_cash_flow: "2500.0000",
    points: [
      {
        bucket_date: "2026-02-01",
        income: "3000.0000",
        expenses: "500.0000",
        net_cash_flow: "2500.0000",
      },
    ],
  });
  vi.mocked(analyticsApi.fetchBudgetUtilizationAnalytics).mockResolvedValue({
    period,
    as_of_date: "2026-02-27",
    items: [],
  });
  vi.mocked(analyticsApi.fetchPeriodComparison).mockResolvedValue({
    current_period: period,
    previous_period: { ...period, preset: "previous_month", start_date: "2025-12-28" },
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
}

function renderAnalytics() {
  return renderWithAuth(<AnalyticsPage />, {
    authenticated: true,
    initialEntries: [routes.analytics],
    routes: [{ path: routes.analytics, element: <AnalyticsPage /> }],
  });
}

describe("AnalyticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAnalyticsSuccess();
  });

  it("renders analytics panels with accessible data tables", async () => {
    renderAnalytics();

    expect(
      await screen.findByRole("heading", { name: /analytics/i }),
    ).toBeInTheDocument();
    const incomeTable = await screen.findByRole("table", {
      name: /income and expenses for the selected period/i,
    });
    expect(within(incomeTable).getByText("$3,000.00")).toBeInTheDocument();
    expect(within(incomeTable).getByText("$500.00")).toBeInTheDocument();

    const categoryTable = await screen.findByRole("table", {
      name: /spending by category for the selected period/i,
    });
    expect(within(categoryTable).getByText("Groceries")).toBeInTheDocument();
  });

  it("shows loading skeletons before data resolves", () => {
    vi.mocked(analyticsApi.fetchIncomeVsExpenses).mockReturnValue(
      new Promise(() => undefined),
    );

    renderAnalytics();

    expect(document.querySelector(".dashboard-skeleton")).toBeTruthy();
  });

  it("shows empty state when category spending has no items", async () => {
    vi.mocked(analyticsApi.fetchSpendingByCategory).mockResolvedValue({
      period,
      reporting_currency: "USD",
      total_expenses: "0.0000",
      items: [],
    });

    renderAnalytics();

    expect(await screen.findByText("No spending in this period")).toBeInTheDocument();
  });

  it("shows error state with retry", async () => {
    const user = userEvent.setup();
    vi.mocked(analyticsApi.fetchIncomeVsExpenses).mockRejectedValue(
      new Error("analytics down"),
    );

    renderAnalytics();

    const retryButtons = await screen.findAllByRole("button", { name: /try again/i });
    await user.click(retryButtons[0]);

    await waitFor(() => {
      expect(analyticsApi.fetchIncomeVsExpenses).toHaveBeenCalledTimes(2);
    });
  });

  it("warns when custom period dates are missing", async () => {
    const user = userEvent.setup();
    renderAnalytics();

    await screen.findByRole("heading", { name: /analytics/i });
    const callsBefore = vi.mocked(analyticsApi.fetchIncomeVsExpenses).mock.calls.length;
    await user.selectOptions(screen.getByLabelText(/^period/i), "custom");

    expect(await screen.findByText(/select a valid period/i)).toBeInTheDocument();
    expect(vi.mocked(analyticsApi.fetchIncomeVsExpenses).mock.calls.length).toBe(
      callsBefore,
    );
  });

  it("refetches when reporting currency changes", async () => {
    const user = userEvent.setup();
    renderAnalytics();

    await screen.findByRole("heading", { name: /analytics/i });
    const initialCalls = vi.mocked(analyticsApi.fetchIncomeVsExpenses).mock.calls
      .length;
    const currency = screen.getByLabelText(/reporting currency/i);
    await user.clear(currency);
    await user.type(currency, "EUR");

    await waitFor(() => {
      expect(
        vi.mocked(analyticsApi.fetchIncomeVsExpenses).mock.calls.length,
      ).toBeGreaterThan(initialCalls);
      expect(analyticsApi.fetchIncomeVsExpenses).toHaveBeenCalledWith(
        expect.objectContaining({ reporting_currency: "EUR" }),
      );
    });
  });
});
