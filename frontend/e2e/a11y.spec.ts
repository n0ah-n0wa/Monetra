import { test, expect } from "@playwright/test";
import { login } from "./helpers/auth";

test.describe("accessibility smoke checks", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("dashboard exposes landmarks and skip link", async ({ page }) => {
    await page.goto("/dashboard");

    await expect(page.getByRole("link", { name: /skip to main content/i })).toBeVisible();
    await expect(page.getByRole("navigation", { name: /main navigation/i })).toBeVisible();
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("keyboard navigation reaches primary actions on transactions page", async ({ page }) => {
    await page.goto("/transactions");

    await page.keyboard.press("Tab");
    const focused = page.locator(":focus");
    await expect(focused).toBeVisible();

    await expect(page.getByRole("link", { name: /new transaction/i })).toBeVisible();
  });

  test("modal dialog traps focus when deleting from accounts", async ({ page }) => {
    await page.goto("/accounts");

    const deleteButton = page.getByRole("button", { name: /^delete /i }).first();
    if ((await deleteButton.count()) === 0) {
      test.skip();
    }

    await deleteButton.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await page.keyboard.press("Tab");
    await expect(dialog.locator(":focus")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });
});
