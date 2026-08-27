import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CategoriesPage } from "@/features/categories/pages/CategoriesPage";
import type { Category } from "@/features/categories/api";
import * as categoriesApi from "@/features/categories/api";
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

vi.mock("@/features/categories/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/categories/api")>(
    "@/features/categories/api",
  );
  return {
    ...actual,
    fetchCategories: vi.fn(),
    createCategory: vi.fn(),
    updateCategory: vi.fn(),
    archiveCategory: vi.fn(),
  };
});

const groceries: Category = {
  id: "cat-1",
  name: "Groceries",
  category_type: "expense",
  icon: null,
  color: "#1f6f5b",
  is_system: false,
  status: "active",
  archived_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const systemCategory: Category = {
  id: "cat-sys",
  name: "Transfer",
  category_type: "universal",
  icon: null,
  color: null,
  is_system: true,
  status: "active",
  archived_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderCategories() {
  return renderWithAuth(<CategoriesPage />, {
    authenticated: true,
    initialEntries: [routes.categories],
    routes: [{ path: routes.categories, element: <CategoriesPage /> }],
  });
}

describe("CategoriesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists categories and marks system categories as read-only", async () => {
    vi.mocked(categoriesApi.fetchCategories).mockResolvedValue({
      items: [groceries, systemCategory],
      page: 1,
      page_size: 100,
      total_items: 2,
      total_pages: 1,
    });

    renderCategories();

    expect(await screen.findByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("Transfer")).toBeInTheDocument();
    expect(screen.getByText("System")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^edit$/i })).toBeInTheDocument();
  });

  it("validates category creation form", async () => {
    const user = userEvent.setup();
    vi.mocked(categoriesApi.fetchCategories).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });

    renderCategories();
    await screen.findByText(/no categories found/i);

    await user.click(screen.getByRole("button", { name: /^add category$/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /create category/i }));
    expect(await screen.findByText(/category name is required/i)).toBeInTheDocument();
  });

  it("creates a category", async () => {
    const user = userEvent.setup();
    vi.mocked(categoriesApi.fetchCategories).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });
    vi.mocked(categoriesApi.createCategory).mockResolvedValue(groceries);

    renderCategories();
    await screen.findByText(/no categories found/i);

    await user.click(screen.getByRole("button", { name: /^add category$/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/^name/i), "Groceries");
    await user.selectOptions(within(dialog).getByLabelText(/^type/i), "expense");
    await user.click(within(dialog).getByRole("button", { name: /create category/i }));

    await waitFor(() => {
      expect(categoriesApi.createCategory).toHaveBeenCalledWith({
        name: "Groceries",
        category_type: "expense",
        icon: null,
        color: null,
      });
    });
  });

  it("edits a user category", async () => {
    const user = userEvent.setup();
    vi.mocked(categoriesApi.fetchCategories).mockResolvedValue({
      items: [groceries],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(categoriesApi.updateCategory).mockResolvedValue({
      ...groceries,
      name: "Food",
    });

    renderCategories();
    await screen.findByText("Groceries");

    await user.click(screen.getByRole("button", { name: /^edit$/i }));
    const dialog = await screen.findByRole("dialog");
    const nameInput = within(dialog).getByLabelText(/^name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Food");
    await user.click(within(dialog).getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(categoriesApi.updateCategory).toHaveBeenCalledWith("cat-1", {
        name: "Food",
        icon: null,
        color: "#1f6f5b",
      });
    });
  });

  it("archives a category after confirmation", async () => {
    const user = userEvent.setup();
    vi.mocked(categoriesApi.fetchCategories).mockResolvedValue({
      items: [groceries],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(categoriesApi.archiveCategory).mockResolvedValue({
      ...groceries,
      status: "archived",
      archived_at: "2026-02-01T00:00:00Z",
    });

    renderCategories();
    await screen.findByText("Groceries");

    await user.click(screen.getByRole("button", { name: /^archive$/i }));
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByRole("heading", { name: /archive category\?/i }),
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /archive category/i }));

    await waitFor(() => {
      expect(categoriesApi.archiveCategory).toHaveBeenCalledWith("cat-1");
    });
  });
});
