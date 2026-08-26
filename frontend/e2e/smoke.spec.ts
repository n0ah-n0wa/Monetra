import { test, expect } from "@playwright/test";

test("home page shows Monetra brand", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Monetra")).toBeVisible();
});
