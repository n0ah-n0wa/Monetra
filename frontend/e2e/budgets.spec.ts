import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { createAccount, createTransaction, listCategories } from "./helpers/api";
import { navigateViaSidebar } from "./helpers/ui";
import { todayIsoDate } from "./helpers/constants";

test.describe("Budgets", () => {
  test("creates a budget and shows utilization", async ({ page, request }) => {
    const user = await registerUser(request, "budget");
    const account = await createAccount(request, user, "Budget Account");
    const categories = await listCategories(request, user);
    const groceries = categories.find((category) => category.name === "Groceries");
    if (!groceries) {
      throw new Error("Expected default Groceries category.");
    }
    await createTransaction(request, user, {
      account_id: account.id,
      category_id: groceries.id,
      transaction_type: "expense",
      amount: "80.0000",
      description: "Budget spend",
      transaction_date: todayIsoDate(),
    });

    await loginViaUi(page, user);
    await navigateViaSidebar(page, "Budgets", "Budgets");
    await page
      .locator(".page-header__actions")
      .getByRole("button", { name: "Add budget" })
      .click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/^name/i).fill("E2E Groceries Budget");
    await dialog.getByLabel(/^amount/i).fill("100.00");
    await dialog.getByLabel(/^period/i).selectOption("monthly");
    await dialog.getByLabel(/^scope/i).selectOption("overall");
    await dialog.getByRole("button", { name: /create budget/i }).click();
    await dialog.waitFor({ state: "hidden" });

    await expect(page.getByText("E2E Groceries Budget")).toBeVisible();
    const budgetCard = page
      .locator(".data-card")
      .filter({ hasText: "E2E Groceries Budget" });
    await expect(budgetCard.getByText(/\$80\.00/)).toBeVisible();
    await expect(budgetCard.getByText(/80(\.00)?%/)).toBeVisible();
  });
});
