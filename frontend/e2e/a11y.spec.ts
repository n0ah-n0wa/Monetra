import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { createAccount } from "./helpers/api";

test.describe("accessibility smoke checks", () => {
  test.beforeEach(async ({ page, request }) => {
    const user = await registerUser(request, "a11y");
    await createAccount(request, user, "Accessibility Account");
    await loginViaUi(page, user);
  });

  test("dashboard exposes landmarks and skip link", async ({ page }) => {
    await page.goto("/dashboard");

    await expect(
      page.getByRole("link", { name: /skip to main content/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("navigation", { name: /main navigation/i }),
    ).toBeVisible();
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("keyboard navigation reaches primary actions on transactions page", async ({
    page,
  }) => {
    await page.goto("/transactions");

    await page.keyboard.press("Tab");
    const focused = page.locator(":focus");
    await expect(focused).toBeVisible();

    await expect(page.getByRole("link", { name: /add transaction/i })).toBeVisible();
  });

  test("modal dialog traps focus when archiving an account", async ({ page }) => {
    await page.goto("/accounts");

    const archiveButton = page.getByRole("button", { name: "Archive" }).first();
    await expect(archiveButton).toBeVisible();

    await archiveButton.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await page.keyboard.press("Tab");
    await expect(dialog.locator(":focus")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });
});
