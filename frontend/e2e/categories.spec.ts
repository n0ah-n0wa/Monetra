import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { createCategoryViaUi } from "./helpers/ui";

test.describe("Categories", () => {
  test("creates a category", async ({ page, request }) => {
    const user = await registerUser(request, "category-create");
    await loginViaUi(page, user);
    const categoryName = `E2E Pets ${Date.now()}`;
    await createCategoryViaUi(page, categoryName, "Expense");
    await expect(page.getByText(categoryName)).toBeVisible();
    const categoryRow = page.locator(".data-card").filter({ hasText: categoryName });
    await expect(categoryRow.getByText("Expense")).toBeVisible();
  });
});
