import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Account } from "@/features/accounts/api";
import * as accountsApi from "@/features/accounts/api";
import type { Category } from "@/features/categories/api";
import * as categoriesApi from "@/features/categories/api";
import type { Transaction } from "@/features/transactions/api";
import * as transactionsApi from "@/features/transactions/api";
import { TransactionCreatePage } from "@/features/transactions/pages/TransactionCreatePage";
import { TransactionDetailPage } from "@/features/transactions/pages/TransactionDetailPage";
import { TransactionsPage } from "@/features/transactions/pages/TransactionsPage";
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

vi.mock("@/features/accounts/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/accounts/api")>(
    "@/features/accounts/api",
  );
  return { ...actual, fetchAccounts: vi.fn() };
});

vi.mock("@/features/categories/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/categories/api")>(
    "@/features/categories/api",
  );
  return { ...actual, fetchCategories: vi.fn() };
});

vi.mock("@/features/transactions/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/transactions/api")>(
    "@/features/transactions/api",
  );
  return {
    ...actual,
    fetchTransactions: vi.fn(),
    fetchTransaction: vi.fn(),
    createTransaction: vi.fn(),
    updateTransaction: vi.fn(),
    deleteTransaction: vi.fn(),
  };
});

const account: Account = {
  id: "acc-1",
  name: "Checking",
  account_type: "bank",
  currency: "USD",
  opening_balance: "0",
  current_balance: "100.0000",
  status: "active",
  archived_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const expenseCategory: Category = {
  id: "cat-exp",
  name: "Groceries",
  category_type: "expense",
  icon: null,
  color: null,
  is_system: false,
  status: "active",
  archived_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const transaction: Transaction = {
  id: "txn-1",
  account_id: "acc-1",
  category_id: "cat-exp",
  transaction_type: "expense",
  amount: "25.0000",
  currency: "USD",
  description: "Coffee shop",
  transaction_date: "2026-02-01",
  notes: null,
  created_at: "2026-02-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
};

function mockReferenceData() {
  vi.mocked(accountsApi.fetchAccounts).mockResolvedValue({
    items: [account],
    page: 1,
    page_size: 100,
    total_items: 1,
    total_pages: 1,
  });
  vi.mocked(categoriesApi.fetchCategories).mockResolvedValue({
    items: [expenseCategory],
    page: 1,
    page_size: 100,
    total_items: 1,
    total_pages: 1,
  });
}

describe("TransactionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockReferenceData();
  });

  it("lists transactions and supports filters", async () => {
    const user = userEvent.setup();
    vi.mocked(transactionsApi.fetchTransactions).mockResolvedValue({
      items: [transaction],
      page: 1,
      page_size: 20,
      total_items: 1,
      total_pages: 1,
    });

    renderWithAuth(<TransactionsPage />, {
      authenticated: true,
      initialEntries: [routes.transactions],
      routes: [{ path: routes.transactions, element: <TransactionsPage /> }],
    });

    expect(await screen.findByText("Coffee shop")).toBeInTheDocument();
    expect(screen.getByText("$25.00")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/^search/i), "coffee");
    await waitFor(() => {
      expect(transactionsApi.fetchTransactions).toHaveBeenCalled();
    });
  });

  it("confirms delete before calling API", async () => {
    const user = userEvent.setup();
    vi.mocked(transactionsApi.fetchTransactions).mockResolvedValue({
      items: [transaction],
      page: 1,
      page_size: 20,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(transactionsApi.deleteTransaction).mockResolvedValue();

    renderWithAuth(<TransactionsPage />, {
      authenticated: true,
      initialEntries: [routes.transactions],
      routes: [{ path: routes.transactions, element: <TransactionsPage /> }],
    });

    await screen.findByText("Coffee shop");
    await user.click(screen.getByRole("button", { name: /^delete$/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(
      within(dialog).getByRole("button", { name: /delete transaction/i }),
    );

    await waitFor(() => {
      expect(transactionsApi.deleteTransaction).toHaveBeenCalledWith("txn-1");
    });
  });
});

describe("TransactionCreatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockReferenceData();
  });

  it("creates a transaction with exact amount string", async () => {
    const user = userEvent.setup();
    vi.mocked(transactionsApi.createTransaction).mockResolvedValue(transaction);

    renderWithAuth(<TransactionCreatePage />, {
      authenticated: true,
      initialEntries: [routes.transactionNew],
      routes: [
        { path: routes.transactionNew, element: <TransactionCreatePage /> },
        { path: routes.transactions, element: <div>Transactions list</div> },
      ],
    });

    await screen.findByRole("heading", { name: /add transaction/i });
    await user.clear(screen.getByLabelText(/^amount/i));
    await user.type(screen.getByLabelText(/^amount/i), "25.0000");
    await user.type(screen.getByLabelText(/^description/i), "Coffee shop");
    await user.click(screen.getByRole("button", { name: /save transaction/i }));

    await waitFor(() => {
      expect(transactionsApi.createTransaction).toHaveBeenCalledWith({
        account_id: "acc-1",
        category_id: "cat-exp",
        transaction_type: "expense",
        amount: "25.0000",
        description: "Coffee shop",
        transaction_date: expect.any(String),
        notes: null,
      });
    });
    expect(await screen.findByText("Transactions list")).toBeInTheDocument();
  });

  it("supports save and add another without navigation", async () => {
    const user = userEvent.setup();
    vi.mocked(transactionsApi.createTransaction).mockResolvedValue(transaction);

    renderWithAuth(<TransactionCreatePage />, {
      authenticated: true,
      initialEntries: [routes.transactionNew],
      routes: [{ path: routes.transactionNew, element: <TransactionCreatePage /> }],
    });

    await screen.findByRole("heading", { name: /add transaction/i });
    await user.type(screen.getByLabelText(/^amount/i), "12.50");
    await user.type(screen.getByLabelText(/^description/i), "Snack");
    await user.click(screen.getByRole("button", { name: /save and add another/i }));

    await waitFor(() => {
      expect(transactionsApi.createTransaction).toHaveBeenCalled();
    });
    expect(screen.getByLabelText(/^amount/i)).toHaveValue("");
    expect(screen.getByLabelText(/^description/i)).toHaveValue("");
    expect(screen.getByText(/1 transaction recorded/i)).toBeInTheDocument();
  });
});

describe("TransactionDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockReferenceData();
    vi.mocked(transactionsApi.fetchTransaction).mockResolvedValue(transaction);
  });

  it("updates a transaction", async () => {
    const user = userEvent.setup();
    vi.mocked(transactionsApi.updateTransaction).mockResolvedValue({
      ...transaction,
      description: "Updated coffee",
    });

    renderWithAuth(<TransactionDetailPage />, {
      authenticated: true,
      initialEntries: ["/transactions/txn-1"],
      routes: [{ path: "/transactions/:id", element: <TransactionDetailPage /> }],
    });

    await screen.findByText("Coffee shop");
    await user.click(screen.getByRole("button", { name: /^edit$/i }));
    const description = screen.getByLabelText(/^description/i);
    await user.clear(description);
    await user.type(description, "Updated coffee");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(transactionsApi.updateTransaction).toHaveBeenCalledWith("txn-1", {
        account_id: "acc-1",
        category_id: "cat-exp",
        transaction_type: "expense",
        amount: "25.0000",
        description: "Updated coffee",
        transaction_date: "2026-02-01",
        notes: null,
      });
    });
  });
});
