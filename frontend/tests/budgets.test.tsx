import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BudgetsPage } from "@/features/budgets/pages/BudgetsPage";
import type { Budget } from "@/features/budgets/api";
import * as budgetsApi from "@/features/budgets/api";
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

vi.mock("@/features/budgets/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/budgets/api")>(
    "@/features/budgets/api",
  );
  return {
    ...actual,
    fetchBudgets: vi.fn(),
    createBudget: vi.fn(),
    updateBudget: vi.fn(),
    archiveBudget: vi.fn(),
  };
});

vi.mock("@/features/categories/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/categories/api")>(
    "@/features/categories/api",
  );
  return {
    ...actual,
    fetchCategories: vi.fn(async () => ({
      items: [
        {
          id: "cat-1",
          name: "Groceries",
          category_type: "expense",
          icon: null,
          color: null,
          is_system: false,
          status: "active",
          archived_at: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    })),
  };
});

const monthlyBudget: Budget = {
  id: "budget-1",
  name: "Groceries",
  amount: "500.0000",
  currency: "USD",
  period: "monthly",
  scope: "overall",
  start_date: "2026-01-01",
  end_date: null,
  warning_threshold_percent: 80,
  categories: [],
  archived_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  utilization: {
    as_of_date: "2026-01-15",
    period_start: "2026-01-01",
    period_end: "2026-01-31",
    budget_amount: "500.0000",
    spent_amount: "200.0000",
    remaining_amount: "300.0000",
    percentage_used: "40.0000",
    status: "healthy",
  },
};

function renderBudgets() {
  return renderWithAuth(<BudgetsPage />, {
    authenticated: true,
    initialEntries: [routes.budgets],
    routes: [{ path: routes.budgets, element: <BudgetsPage /> }],
  });
}

describe("BudgetsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists budgets with utilization metrics", async () => {
    vi.mocked(budgetsApi.fetchBudgets).mockResolvedValue({
      items: [monthlyBudget],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });

    renderBudgets();

    expect(await screen.findByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("healthy")).toBeInTheDocument();
    expect(screen.getByText("$500.00")).toBeInTheDocument();
    expect(screen.getByText("$200.00")).toBeInTheDocument();
    expect(screen.getByText("$300.00")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
  });

  it("validates budget creation form", async () => {
    const user = userEvent.setup();
    vi.mocked(budgetsApi.fetchBudgets).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });

    renderBudgets();
    await screen.findByText(/no budgets yet/i);

    await user.click(screen.getByRole("button", { name: /^add budget$/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /create budget/i }));
    expect(await screen.findByText(/budget name is required/i)).toBeInTheDocument();
  });

  it("creates a budget", async () => {
    const user = userEvent.setup();
    vi.mocked(budgetsApi.fetchBudgets).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });
    vi.mocked(budgetsApi.createBudget).mockResolvedValue(monthlyBudget);

    renderBudgets();
    await screen.findByText(/no budgets yet/i);

    await user.click(screen.getByRole("button", { name: /^add budget$/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/^name/i), "Groceries");
    await user.type(within(dialog).getByLabelText(/^amount/i), "500");
    await user.click(within(dialog).getByRole("button", { name: /create budget/i }));

    await waitFor(() => {
      expect(budgetsApi.createBudget).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Groceries",
          amount: "500",
          currency: "USD",
          period: "monthly",
          scope: "overall",
        }),
      );
    });
  });

  it("edits a budget", async () => {
    const user = userEvent.setup();
    vi.mocked(budgetsApi.fetchBudgets).mockResolvedValue({
      items: [monthlyBudget],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(budgetsApi.updateBudget).mockResolvedValue({
      ...monthlyBudget,
      name: "Food",
    });

    renderBudgets();
    await screen.findByText("Groceries");

    await user.click(screen.getByRole("button", { name: /^edit$/i }));
    const dialog = await screen.findByRole("dialog");
    const nameInput = within(dialog).getByLabelText(/^name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Food");
    await user.click(within(dialog).getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(budgetsApi.updateBudget).toHaveBeenCalledWith(
        "budget-1",
        expect.objectContaining({ name: "Food" }),
      );
    });
  });

  it("archives a budget after confirmation", async () => {
    const user = userEvent.setup();
    vi.mocked(budgetsApi.fetchBudgets).mockResolvedValue({
      items: [monthlyBudget],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(budgetsApi.archiveBudget).mockResolvedValue({
      ...monthlyBudget,
      archived_at: "2026-02-01T00:00:00Z",
    });

    renderBudgets();
    await screen.findByText("Groceries");

    await user.click(screen.getByRole("button", { name: /^archive$/i }));
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByRole("heading", { name: /archive budget\?/i }),
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /archive budget/i }));

    await waitFor(() => {
      expect(budgetsApi.archiveBudget).toHaveBeenCalledWith("budget-1");
    });
  });
});
