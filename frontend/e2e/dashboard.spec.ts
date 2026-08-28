import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { createAccount, createTransaction, listCategories } from "./helpers/api";
import { navigateViaSidebar } from "./helpers/ui";

test.describe("Dashboard analytics", () => {
  test("shows dashboard widgets after activity", async ({ page, request }) => {
    const user = await registerUser(request, "dashboard");
    const account = await createAccount(request, user, "Dashboard Account");
    const categories = await listCategories(request, user);
    const salary = categories.find((category) => category.name === "Salary");
    const groceries = categories.find((category) => category.name === "Groceries");
    if (!salary || !groceries) {
      throw new Error("Expected default categories.");
    }
    await createTransaction(request, user, {
      account_id: account.id,
      category_id: salary.id,
      transaction_type: "income",
      amount: "2000.0000",
      description: "Dashboard income",
    });
    await createTransaction(request, user, {
      account_id: account.id,
      category_id: groceries.id,
      transaction_type: "expense",
      amount: "50.0000",
      description: "Dashboard groceries",
    });

    await loginViaUi(page, user);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("Dashboard income")).toBeVisible();
    await expect(page.getByText("Groceries")).toBeVisible();

    await navigateViaSidebar(page, "Analytics", "Analytics");
    await expect(
      page.getByRole("heading", { name: /income vs expenses/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /spending by category/i }),
    ).toBeVisible();
  });
});
