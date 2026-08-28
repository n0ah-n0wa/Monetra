import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { createAccount, createTransaction, listCategories } from "./helpers/api";
import {
  createAccountViaUi,
  createTransactionViaUi,
  navigateViaSidebar,
} from "./helpers/ui";

test.describe("Transactions", () => {
  test("creates an income transaction", async ({ page, request }) => {
    const user = await registerUser(request, "income");
    await loginViaUi(page, user);
    await createAccountViaUi(page, "Income Account");
    await createTransactionViaUi(page, {
      type: "income",
      amount: "1500.00",
      description: "E2E salary deposit",
      categoryName: "Salary",
    });
    await expect(page.getByText("E2E salary deposit")).toBeVisible();
    const incomeRow = page.getByRole("row").filter({ hasText: "E2E salary deposit" });
    await expect(incomeRow.getByText("Income", { exact: true })).toBeVisible();
  });

  test("creates an expense transaction", async ({ page, request }) => {
    const user = await registerUser(request, "expense");
    await loginViaUi(page, user);
    await createAccountViaUi(page, "Spending Account");
    await createTransactionViaUi(page, {
      type: "expense",
      amount: "42.50",
      description: "E2E grocery run",
      categoryName: "Groceries",
    });
    await expect(page.getByText("E2E grocery run")).toBeVisible();
    const groceryRow = page.getByRole("row").filter({ hasText: "E2E grocery run" });
    await expect(groceryRow.getByText("Expense", { exact: true })).toBeVisible();
  });

  test("edits a transaction", async ({ page, request }) => {
    const user = await registerUser(request, "edit-tx");
    const account = await createAccount(request, user, "Edit Account");
    const categories = await listCategories(request, user);
    const food = categories.find((category) => category.name === "Food");
    if (!food) {
      throw new Error("Expected default Food category.");
    }
    await createTransaction(request, user, {
      account_id: account.id,
      category_id: food.id,
      transaction_type: "expense",
      amount: "10.0000",
      description: "Original lunch",
    });

    await loginViaUi(page, user);
    await navigateViaSidebar(page, "Transactions", "Transactions");
    const lunchRow = page.getByRole("row").filter({ hasText: "Original lunch" });
    await lunchRow.getByRole("link", { name: "Original lunch" }).click();
    await page.getByRole("button", { name: "Edit" }).click();
    await page.getByLabel(/^description/i).fill("Updated lunch");
    await page.getByRole("button", { name: /save changes/i }).click();
    await expect(page.getByRole("heading", { name: "Updated lunch" })).toBeVisible();
  });

  test("filters transactions by description", async ({ page, request }) => {
    const user = await registerUser(request, "filter-tx");
    const account = await createAccount(request, user, "Filter Account");
    const categories = await listCategories(request, user);
    const groceries = categories.find((category) => category.name === "Groceries");
    if (!groceries) {
      throw new Error("Expected default Groceries category.");
    }
    await createTransaction(request, user, {
      account_id: account.id,
      category_id: groceries.id,
      transaction_type: "expense",
      amount: "12.0000",
      description: "Alpha filter marker",
    });
    await createTransaction(request, user, {
      account_id: account.id,
      category_id: groceries.id,
      transaction_type: "expense",
      amount: "8.0000",
      description: "Beta other purchase",
    });

    await loginViaUi(page, user);
    await navigateViaSidebar(page, "Transactions", "Transactions");
    await page.getByLabel("Search").fill("Alpha filter marker");
    await expect(page.getByText("Alpha filter marker")).toBeVisible();
    await expect(page.getByText("Beta other purchase")).not.toBeVisible();
  });
});
