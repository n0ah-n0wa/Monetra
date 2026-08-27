import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ImportJob } from "@/features/imports/api";
import * as importsApi from "@/features/imports/api";
import { ImportPage } from "@/features/imports/pages/ImportPage";
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

vi.mock("@/features/imports/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/imports/api")>(
    "@/features/imports/api",
  );
  return {
    ...actual,
    uploadImportFile: vi.fn(),
    fetchImportJobs: vi.fn(),
    confirmImportJob: vi.fn(),
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

const previewJob: ImportJob = {
  id: "import-1",
  target_account_id: "acct-1",
  original_filename: "transactions.csv",
  content_type: "text/csv",
  status: "preview",
  stats: {
    total_rows: 3,
    valid_rows: 2,
    invalid_rows: 1,
    imported_rows: 0,
    skipped_rows: 0,
    duplicate_rows: 1,
  },
  preview_rows: [
    {
      row_number: 2,
      transaction_date: "2026-01-15",
      transaction_type: "expense",
      amount: "45.5000",
      description: "Groceries",
      category: "Food",
      category_id: "cat-1",
      external_reference: null,
      notes: null,
      is_duplicate: false,
      duplicate_reason: null,
    },
    {
      row_number: 4,
      transaction_date: "2026-01-20",
      transaction_type: "income",
      amount: "1200.0000",
      description: "Paycheck",
      category: "Salary",
      category_id: "cat-2",
      external_reference: "pay-jan",
      notes: null,
      is_duplicate: true,
      duplicate_reason: "Matches existing transaction",
    },
  ],
  errors: [
    {
      row_number: 3,
      code: "invalid_amount",
      message: "Amount must be positive",
      raw: { amount: "-5" },
    },
  ],
  completed_at: null,
  created_at: "2026-02-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
};

const completedJob: ImportJob = {
  ...previewJob,
  status: "completed",
  stats: {
    ...previewJob.stats,
    imported_rows: 1,
    skipped_rows: 2,
  },
  completed_at: "2026-02-01T00:05:00Z",
};

function renderImportPage() {
  return renderWithAuth(<ImportPage />, {
    authenticated: true,
    initialEntries: [routes.import],
    routes: [{ path: routes.import, element: <ImportPage /> }],
  });
}

describe("ImportPage", () => {
  beforeEach(() => {
    vi.mocked(importsApi.fetchImportJobs).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 5,
      total_items: 0,
      total_pages: 0,
    });
    vi.mocked(importsApi.uploadImportFile).mockReset();
    vi.mocked(importsApi.confirmImportJob).mockReset();
  });

  it("renders upload form and recent imports", async () => {
    renderImportPage();

    expect(
      await screen.findByRole("heading", { name: "Import transactions" }),
    ).toBeInTheDocument();
    expect(await screen.findByLabelText(/target account/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/csv file/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /upload and preview/i })).toBeDisabled();
    expect(screen.getByText(/no imports yet/i)).toBeInTheDocument();
  });

  it("uploads a file and shows preview stats and tables", async () => {
    const user = userEvent.setup();
    vi.mocked(importsApi.uploadImportFile).mockResolvedValue(previewJob);

    renderImportPage();
    await screen.findByLabelText(/target account/i);

    await user.selectOptions(screen.getByLabelText(/target account/i), "acct-1");
    const file = new File(
      ["transaction_date,transaction_type,amount,description,category\n"],
      "transactions.csv",
      { type: "text/csv" },
    );
    await user.upload(screen.getByLabelText(/csv file/i), file);

    await user.click(screen.getByRole("button", { name: /upload and preview/i }));

    expect(await screen.findByText(/preview: transactions.csv/i)).toBeInTheDocument();
    const statsHeading = screen.getByRole("heading", { name: "Import statistics" });
    const statsSection = statsHeading.closest("section");
    expect(statsSection).not.toBeNull();
    expect(within(statsSection!).getByText("Valid rows")).toBeInTheDocument();
    expect(within(statsSection!).getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Validation errors" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/amount must be positive/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Duplicate rows" })).toBeInTheDocument();
    expect(screen.getAllByText(/matches existing transaction/i).length).toBeGreaterThan(
      0,
    );
  });

  it("blocks confirm until invalid rows are acknowledged", async () => {
    const user = userEvent.setup();
    vi.mocked(importsApi.uploadImportFile).mockResolvedValue(previewJob);

    renderImportPage();
    await screen.findByLabelText(/target account/i);
    await user.selectOptions(screen.getByLabelText(/target account/i), "acct-1");
    await user.upload(
      screen.getByLabelText(/csv file/i),
      new File(["a"], "transactions.csv", { type: "text/csv" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and preview/i }));
    await screen.findByText(/preview: transactions.csv/i);

    const importButton = screen.getByRole("button", { name: /import valid rows/i });
    expect(importButton).toBeDisabled();

    await user.click(
      screen.getByRole("checkbox", {
        name: /i reviewed the validation errors/i,
      }),
    );
    expect(importButton).toBeEnabled();
  });

  it("confirms import after acknowledgment and shows result", async () => {
    const user = userEvent.setup();
    vi.mocked(importsApi.uploadImportFile).mockResolvedValue(previewJob);
    vi.mocked(importsApi.confirmImportJob).mockResolvedValue(completedJob);

    renderImportPage();
    await screen.findByLabelText(/target account/i);
    await user.selectOptions(screen.getByLabelText(/target account/i), "acct-1");
    await user.upload(
      screen.getByLabelText(/csv file/i),
      new File(["a"], "transactions.csv", { type: "text/csv" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and preview/i }));
    await screen.findByText(/preview: transactions.csv/i);

    await user.click(
      screen.getByRole("checkbox", {
        name: /i reviewed the validation errors/i,
      }),
    );
    await user.click(screen.getByRole("button", { name: /import valid rows/i }));

    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /confirm import/i }));

    await waitFor(() => {
      expect(importsApi.confirmImportJob).toHaveBeenCalledWith("import-1", {
        skip_duplicates: true,
      });
    });

    expect(await screen.findByText(/import completed/i)).toBeInTheDocument();
    expect(screen.getByText(/final statistics/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view transactions/i })).toHaveAttribute(
      "href",
      routes.transactions,
    );
  });

  it("shows warning when no valid rows can be imported", async () => {
    const user = userEvent.setup();
    const allInvalidJob: ImportJob = {
      ...previewJob,
      stats: {
        total_rows: 1,
        valid_rows: 0,
        invalid_rows: 1,
        imported_rows: 0,
        skipped_rows: 0,
        duplicate_rows: 0,
      },
      preview_rows: [],
      errors: previewJob.errors,
    };
    vi.mocked(importsApi.uploadImportFile).mockResolvedValue(allInvalidJob);

    renderImportPage();
    await screen.findByLabelText(/target account/i);
    await user.selectOptions(screen.getByLabelText(/target account/i), "acct-1");
    await user.upload(
      screen.getByLabelText(/csv file/i),
      new File(["a"], "bad.csv", { type: "text/csv" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and preview/i }));

    expect(await screen.findByText(/nothing to import/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /import valid rows/i })).toBeDisabled();
  });
});
