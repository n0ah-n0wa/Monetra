import { test, expect } from "@playwright/test";
import fs from "node:fs/promises";
import { loginViaUi, registerUser } from "./helpers/auth";
import {
  createAccount,
  createTransaction,
  exportTransactionsCsv,
  listCategories,
} from "./helpers/api";
import { navigateViaSidebar } from "./helpers/ui";

test.describe("CSV export", () => {
  test("exports transactions from the UI", async ({ page, request }) => {
    const user = await registerUser(request, "export-ui");
    const account = await createAccount(request, user, "Export Account");
    const categories = await listCategories(request, user);
    const food = categories.find((category) => category.name === "Food");
    if (!food) {
      throw new Error("Expected default Food category.");
    }
    await createTransaction(request, user, {
      account_id: account.id,
      category_id: food.id,
      transaction_type: "expense",
      amount: "19.9900",
      description: "E2E export marker",
    });

    await loginViaUi(page, user);
    await navigateViaSidebar(page, "Transactions", "Transactions");

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export CSV" }).click();
    const download = await downloadPromise;
    const csv = await fs.readFile((await download.path())!, "utf8");
    expect(csv).toContain("transaction_date");
    expect(csv).toContain("E2E export marker");
  });

  test("exports transactions via API", async ({ request }) => {
    const user = await registerUser(request, "export-api");
    const account = await createAccount(request, user, "API Export Account");
    const categories = await listCategories(request, user);
    const food = categories.find((category) => category.name === "Food");
    if (!food) {
      throw new Error("Expected default Food category.");
    }
    await createTransaction(request, user, {
      account_id: account.id,
      category_id: food.id,
      transaction_type: "expense",
      amount: "5.0000",
      description: "API export marker",
    });

    const csv = await exportTransactionsCsv(request, user);
    expect(csv).toContain("API export marker");
    expect(csv).toContain("transaction_date");
  });
});
