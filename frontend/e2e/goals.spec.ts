import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { navigateViaSidebar } from "./helpers/ui";

test.describe("Goals", () => {
  test("creates a financial goal", async ({ page, request }) => {
    const user = await registerUser(request, "goal");
    await loginViaUi(page, user);
    await navigateViaSidebar(page, "Goals", "Goals");
    await page
      .locator(".page-header__actions")
      .getByRole("button", { name: "Add goal" })
      .click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/^name/i).fill("E2E Emergency Fund");
    await dialog.getByLabel(/target amount/i).fill("5000.00");
    await dialog.getByLabel(/current amount/i).fill("500.00");
    await dialog.getByRole("button", { name: /create goal/i }).click();
    await dialog.waitFor({ state: "hidden" });
    await expect(page.getByText("E2E Emergency Fund")).toBeVisible();
    await expect(page.getByText(/10\.0+%|10%/)).toBeVisible();
  });
});
