import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { buildImportCsv } from "./helpers/api";
import { createAccountViaUi, navigateViaSidebar } from "./helpers/ui";
import path from "node:path";
import fs from "node:fs/promises";
import os from "node:os";

test.describe("Notifications", () => {
  test("shows import completed notification", async ({ page, request }) => {
    const user = await registerUser(request, "notifications");
    await loginViaUi(page, user);
    await createAccountViaUi(page, "Notify Account");

    const csvPath = path.join(os.tmpdir(), `monetra-notify-${Date.now()}.csv`);
    await fs.writeFile(
      csvPath,
      buildImportCsv([
        {
          transaction_date: "2026-02-11",
          transaction_type: "income",
          amount: "100.0000",
          description: "E2E notify income",
          category: "Salary",
        },
      ]),
      "utf8",
    );

    await navigateViaSidebar(page, "Import", "Import transactions");
    await page
      .getByLabel(/target account/i)
      .selectOption({ label: "Notify Account (USD)" });
    await page.getByLabel(/csv file/i).setInputFiles(csvPath);
    await page.getByRole("button", { name: /upload and preview/i }).click();
    await expect(page.getByText("E2E notify income")).toBeVisible();
    await page.getByRole("button", { name: /import valid rows/i }).click();
    const confirmDialog = page.getByRole("dialog");
    if (await confirmDialog.isVisible()) {
      await confirmDialog.getByRole("button", { name: /import valid rows/i }).click();
    }
    await expect(page.getByText(/completed/i)).toBeVisible({ timeout: 30_000 });

    await navigateViaSidebar(page, "Notifications", "Notifications");
    await expect(page.getByRole("heading", { name: /import completed/i })).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: "Mark as read" }).click();
    await expect(page.getByRole("button", { name: "Mark as read" })).toHaveCount(0);

    await fs.unlink(csvPath);
  });
});
