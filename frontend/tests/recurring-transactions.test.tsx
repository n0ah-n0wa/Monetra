import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RecurringTransactionsPage } from "@/features/recurring-transactions/pages/RecurringTransactionsPage";
import type { RecurringTransaction } from "@/features/recurring-transactions/api";
import * as recurringApi from "@/features/recurring-transactions/api";
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

vi.mock("@/features/recurring-transactions/api", async () => {
  const actual = await vi.importActual<
    typeof import("@/features/recurring-transactions/api")
  >("@/features/recurring-transactions/api");
  return {
    ...actual,
    fetchRecurringTransactions: vi.fn(),
    createRecurringTransaction: vi.fn(),
    updateRecurringTransaction: vi.fn(),
    archiveRecurringTransaction: vi.fn(),
  };
});

vi.mock("@/features/accounts/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/accounts/api")>(
    "@/features/accounts/api",
  );
  return {
    ...actual,
    fetchAccounts: vi.fn(async () => ({
      items: [
        {
          id: "acct-1",
          name: "Checking",
          account_type: "bank",
          currency: "USD",
          opening_balance: "1000.0000",
          current_balance: "1000.0000",
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
          name: "Rent",
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

const rentRecurring: RecurringTransaction = {
  id: "rec-1",
  account_id: "acct-1",
  category_id: "cat-1",
  transaction_type: "expense",
  amount: "1200.0000",
  currency: "USD",
  description: "Monthly rent",
  frequency: "monthly",
  start_date: "2026-01-01",
  end_date: null,
  next_execution_date: "2026-03-01",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderRecurringPage() {
  return renderWithAuth(<RecurringTransactionsPage />, {
    authenticated: true,
    initialEntries: [routes.recurring],
    routes: [{ path: routes.recurring, element: <RecurringTransactionsPage /> }],
  });
}

describe("RecurringTransactionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists recurring transactions with schedule details", async () => {
    vi.mocked(recurringApi.fetchRecurringTransactions).mockResolvedValue({
      items: [rentRecurring],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });

    renderRecurringPage();

    expect(await screen.findByText("Monthly rent")).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("Active");
    expect(screen.getByText("$1,200.00")).toBeInTheDocument();
    expect(screen.getByText("Checking")).toBeInTheDocument();
    expect(screen.getByText("Rent")).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("Monthly");
    expect(screen.getByRole("listitem")).toHaveTextContent("Expense");
  });

  it("validates recurring transaction creation form", async () => {
    const user = userEvent.setup();
    vi.mocked(recurringApi.fetchRecurringTransactions).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });

    renderRecurringPage();
    await screen.findByText(/no recurring transactions/i);

    await user.click(
      screen.getByRole("button", { name: /^add recurring transaction$/i }),
    );
    const dialog = await screen.findByRole("dialog");
    await user.click(
      within(dialog).getByRole("button", { name: /create recurring transaction/i }),
    );
    expect(await screen.findByText(/amount is required/i)).toBeInTheDocument();
  });

  it("creates a recurring transaction", async () => {
    const user = userEvent.setup();
    vi.mocked(recurringApi.fetchRecurringTransactions).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });
    vi.mocked(recurringApi.createRecurringTransaction).mockResolvedValue(rentRecurring);

    renderRecurringPage();
    await screen.findByText(/no recurring transactions/i);

    await user.click(
      screen.getByRole("button", { name: /^add recurring transaction$/i }),
    );
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/^amount/i), "1200");
    await user.type(within(dialog).getByLabelText(/^description/i), "Monthly rent");
    await user.click(
      within(dialog).getByRole("button", { name: /create recurring transaction/i }),
    );

    await waitFor(() => {
      expect(recurringApi.createRecurringTransaction).toHaveBeenCalledWith(
        expect.objectContaining({
          account_id: "acct-1",
          category_id: "cat-1",
          amount: "1200",
          description: "Monthly rent",
          frequency: "monthly",
          transaction_type: "expense",
        }),
      );
    });
  });

  it("edits a recurring transaction", async () => {
    const user = userEvent.setup();
    vi.mocked(recurringApi.fetchRecurringTransactions).mockResolvedValue({
      items: [rentRecurring],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(recurringApi.updateRecurringTransaction).mockResolvedValue({
      ...rentRecurring,
      description: "Updated rent",
    });

    renderRecurringPage();
    await screen.findByText("Monthly rent");

    await user.click(screen.getByRole("button", { name: /^edit$/i }));
    const dialog = await screen.findByRole("dialog");
    const descriptionInput = within(dialog).getByLabelText(/^description/i);
    await user.clear(descriptionInput);
    await user.type(descriptionInput, "Updated rent");
    await user.click(within(dialog).getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(recurringApi.updateRecurringTransaction).toHaveBeenCalledWith(
        "rec-1",
        expect.objectContaining({ description: "Updated rent" }),
      );
    });
  });

  it("disables a recurring transaction after confirmation", async () => {
    const user = userEvent.setup();
    vi.mocked(recurringApi.fetchRecurringTransactions).mockResolvedValue({
      items: [rentRecurring],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(recurringApi.updateRecurringTransaction).mockResolvedValue({
      ...rentRecurring,
      is_active: false,
    });

    renderRecurringPage();
    await screen.findByText("Monthly rent");

    await user.click(screen.getByRole("button", { name: /^disable$/i }));
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByRole("heading", { name: /disable recurring transaction\?/i }),
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /^disable$/i }));

    await waitFor(() => {
      expect(recurringApi.updateRecurringTransaction).toHaveBeenCalledWith("rec-1", {
        is_active: false,
      });
    });
  });

  it("archives a recurring transaction after confirmation", async () => {
    const user = userEvent.setup();
    vi.mocked(recurringApi.fetchRecurringTransactions).mockResolvedValue({
      items: [rentRecurring],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(recurringApi.archiveRecurringTransaction).mockResolvedValue({
      ...rentRecurring,
      is_active: false,
    });

    renderRecurringPage();
    await screen.findByText("Monthly rent");

    await user.click(screen.getByRole("button", { name: /^archive$/i }));
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByRole("heading", { name: /archive recurring transaction\?/i }),
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /^archive$/i }));

    await waitFor(() => {
      expect(recurringApi.archiveRecurringTransaction).toHaveBeenCalledWith("rec-1");
    });
  });
});
