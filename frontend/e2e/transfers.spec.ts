import { test, expect } from "@playwright/test";
import { loginViaUi, registerUser } from "./helpers/auth";
import { navigateViaSidebar } from "./helpers/ui";
import { createAccount, createTransfer, fetchAccountBalance } from "./helpers/api";

test.describe("Transfers", () => {
  test("creates a transfer between accounts", async ({ page, request }) => {
    const user = await registerUser(request, "transfer");
    const source = await createAccount(request, user, "Transfer Source", {
      opening_balance: "1000.0000",
    });
    const destination = await createAccount(request, user, "Transfer Destination", {
      opening_balance: "200.0000",
    });

    await createTransfer(request, user, {
      source_account_id: source.id,
      destination_account_id: destination.id,
      source_amount: "150.0000",
      description: "E2E account transfer",
    });

    const sourceBalance = await fetchAccountBalance(request, user, source.id);
    const destinationBalance = await fetchAccountBalance(request, user, destination.id);
    expect(sourceBalance).toBe("850.0000");
    expect(destinationBalance).toBe("350.0000");

    await loginViaUi(page, user);
    await navigateViaSidebar(page, "Accounts", "Accounts");
    await expect(page.getByRole("link", { name: "Transfer Source" })).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Transfer Destination" }),
    ).toBeVisible();
    await expect(page.getByText(/850\.0000|850\.00/)).toBeVisible();
    await expect(page.getByText(/350\.0000|350\.00/)).toBeVisible();
  });
});
