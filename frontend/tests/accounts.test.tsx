import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AccountsPage } from "@/features/accounts/pages/AccountsPage";
import { AccountDetailPage } from "@/features/accounts/pages/AccountDetailPage";
import type { Account } from "@/features/accounts/api";
import * as accountsApi from "@/features/accounts/api";
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
  return {
    ...actual,
    fetchAccounts: vi.fn(),
    fetchAccount: vi.fn(),
    createAccount: vi.fn(),
    updateAccount: vi.fn(),
    archiveAccount: vi.fn(),
  };
});

const checkingAccount: Account = {
  id: "acc-1",
  name: "Checking",
  account_type: "bank",
  currency: "USD",
  opening_balance: "100.00",
  current_balance: "250.50",
  status: "active",
  archived_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderAccounts(initialRoute = routes.accounts) {
  return renderWithAuth(<AccountsPage />, {
    authenticated: true,
    initialEntries: [initialRoute],
    routes: [
      { path: routes.accounts, element: <AccountsPage /> },
      { path: "/accounts/:id", element: <AccountDetailPage /> },
    ],
  });
}

describe("AccountsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty state when there are no accounts", async () => {
    vi.mocked(accountsApi.fetchAccounts).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });

    renderAccounts();

    expect(await screen.findByText(/no accounts yet/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /add account/i })).toHaveLength(2);
  });

  it("lists accounts and opens create dialog with validation", async () => {
    const user = userEvent.setup();
    vi.mocked(accountsApi.fetchAccounts).mockResolvedValue({
      items: [checkingAccount],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });

    renderAccounts();

    expect(await screen.findByText("Checking")).toBeInTheDocument();
    expect(screen.getByText(/\$250\.50/)).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: /^add account$/i })[0]!);
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toBeInTheDocument();
    await user.clear(within(dialog).getByLabelText(/^name/i));
    await user.click(within(dialog).getByRole("button", { name: /create account/i }));
    expect(await screen.findByText(/account name is required/i)).toBeInTheDocument();
  });

  it("creates an account through the dialog", async () => {
    const user = userEvent.setup();
    vi.mocked(accountsApi.fetchAccounts).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });
    vi.mocked(accountsApi.createAccount).mockResolvedValue({
      ...checkingAccount,
      id: "acc-2",
      name: "Savings",
      account_type: "savings",
    });

    renderAccounts();
    await screen.findByText(/no accounts yet/i);

    await user.click(screen.getAllByRole("button", { name: /^add account$/i })[0]!);
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/^name/i), "Savings");
    await user.selectOptions(within(dialog).getByLabelText(/^type/i), "savings");
    await user.clear(within(dialog).getByLabelText(/^currency/i));
    await user.type(within(dialog).getByLabelText(/^currency/i), "USD");
    await user.clear(within(dialog).getByLabelText(/opening balance/i));
    await user.type(within(dialog).getByLabelText(/opening balance/i), "50");
    await user.click(within(dialog).getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(accountsApi.createAccount).toHaveBeenCalledWith({
        name: "Savings",
        account_type: "savings",
        currency: "USD",
        opening_balance: "50",
      });
    });
  });

  it("confirms archival before calling the API", async () => {
    const user = userEvent.setup();
    vi.mocked(accountsApi.fetchAccounts).mockResolvedValue({
      items: [checkingAccount],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(accountsApi.archiveAccount).mockResolvedValue({
      ...checkingAccount,
      status: "archived",
      archived_at: "2026-02-01T00:00:00Z",
    });

    renderAccounts();
    await screen.findByText("Checking");

    await user.click(screen.getByRole("button", { name: /^archive$/i }));
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByRole("heading", { name: /archive account\?/i }),
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /archive account/i }));

    await waitFor(() => {
      expect(accountsApi.archiveAccount).toHaveBeenCalledWith("acc-1");
    });
  });

  it("shows error recovery when loading fails", async () => {
    const user = userEvent.setup();
    vi.mocked(accountsApi.fetchAccounts).mockRejectedValue(new Error("Network down"));

    renderAccounts();
    expect(await screen.findByText(/unable to load accounts/i)).toBeInTheDocument();

    vi.mocked(accountsApi.fetchAccounts).mockResolvedValue({
      items: [checkingAccount],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("Checking")).toBeInTheDocument();
  });
});
