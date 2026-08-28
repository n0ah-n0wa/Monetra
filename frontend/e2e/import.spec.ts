import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { buildImportCsv } from "./helpers/api";
import { createAccountViaUi } from "./helpers/ui";
import { navigateViaSidebar } from "./helpers/ui";
import path from "node:path";
import fs from "node:fs/promises";
import os from "node:os";

test.describe("CSV import", () => {
  test("uploads, previews, and imports valid rows", async ({ page, request }) => {
    const user = await registerUser(request, "import");
    await loginViaUi(page, user);
    await createAccountViaUi(page, "Import Target");

    const csvPath = path.join(os.tmpdir(), `monetra-import-${Date.now()}.csv`);
    await fs.writeFile(
      csvPath,
      buildImportCsv([
        {
          transaction_date: "2026-02-10",
          transaction_type: "expense",
          amount: "25.5000",
          description: "E2E imported coffee",
          category: "Food",
        },
      ]),
      "utf8",
    );

    await navigateViaSidebar(page, "Import", "Import transactions");
    await page
      .getByLabel(/target account/i)
      .selectOption({ label: "Import Target (USD)" });
    await page.getByLabel(/csv file/i).setInputFiles(csvPath);
    await page.getByRole("button", { name: /upload and preview/i }).click();

    await expect(page.getByText("E2E imported coffee")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /import valid rows/i }),
    ).toBeEnabled();
    await page.getByRole("button", { name: /import valid rows/i }).click();
    const confirmDialog = page.getByRole("dialog");
    if (await confirmDialog.isVisible()) {
      await confirmDialog.getByRole("button", { name: /import valid rows/i }).click();
    }

    await expect(page.getByText(/import completed|completed/i)).toBeVisible({
      timeout: 30_000,
    });
    await navigateViaSidebar(page, "Transactions", "Transactions");
    await expect(page.getByText("E2E imported coffee")).toBeVisible();

    await fs.unlink(csvPath);
  });
});
