import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { createAccountViaUi } from "./helpers/ui";

test.describe("Accounts", () => {
  test("creates an account", async ({ page, request }) => {
    const user = await registerUser(request, "account-create");
    await loginViaUi(page, user);
    await createAccountViaUi(page, "E2E Checking", {
      opening_balance: "2500.00",
      currency: "USD",
    });
    await expect(page.getByRole("link", { name: "E2E Checking" })).toBeVisible();
    await expect(page.getByText(/2,?500\.00/)).toBeVisible();
  });

  test("shows account detail", async ({ page, request }) => {
    const user = await registerUser(request, "account-detail");
    await loginViaUi(page, user);
    await createAccountViaUi(page, "Savings Vault");
    await page.getByRole("link", { name: "Savings Vault" }).click();
    await expect(page.getByRole("heading", { name: "Savings Vault" })).toBeVisible();
    await expect(page).toHaveURL(/\/accounts\/.+/);
  });
});
