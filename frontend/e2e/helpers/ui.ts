import type { Page } from "@playwright/test";
import { routes } from "./constants";

async function openMobileNavIfNeeded(page: Page): Promise<void> {
  const menuButton = page.getByRole("button", { name: "Toggle navigation menu" });
  if (await menuButton.isVisible()) {
    await menuButton.click();
  }
}

function pageHeaderButton(page: Page, name: string | RegExp) {
  return page.locator(".page-header__actions").getByRole("button", { name });
}

function pageHeaderLink(page: Page, name: string | RegExp) {
  return page.locator(".page-header__actions").getByRole("link", { name });
}

export async function navigateViaSidebar(
  page: Page,
  linkLabel: string,
  expectedHeading: string | RegExp,
): Promise<void> {
  await openMobileNavIfNeeded(page);
  await page
    .getByRole("complementary", { name: "Main navigation" })
    .getByRole("link", { name: linkLabel })
    .click();
  await page.getByRole("heading", { name: expectedHeading }).waitFor();
}

export async function createAccountViaUi(
  page: Page,
  name: string,
  options: { opening_balance?: string; currency?: string } = {},
): Promise<void> {
  await navigateViaSidebar(page, "Accounts", "Accounts");
  await pageHeaderButton(page, "Add account").click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(/^name/i).fill(name);
  if (options.currency) {
    await dialog.getByLabel(/^currency/i).fill(options.currency);
  }
  if (options.opening_balance) {
    await dialog.getByLabel(/opening balance/i).fill(options.opening_balance);
  }
  await dialog.getByRole("button", { name: /create account/i }).click();
  await dialog.waitFor({ state: "hidden" });
  await page.getByRole("link", { name }).waitFor();
}

export async function createCategoryViaUi(
  page: Page,
  name: string,
  type: "Income" | "Expense",
): Promise<void> {
  await navigateViaSidebar(page, "Categories", "Categories");
  await pageHeaderButton(page, "Add category").click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(/^name/i).fill(name);
  await dialog.getByLabel(/^type/i).selectOption(type);
  await dialog.getByRole("button", { name: /create category/i }).click();
  await dialog.waitFor({ state: "hidden" });
  await page.getByText(name).waitFor();
}

export async function createTransactionViaUi(
  page: Page,
  options: {
    type: "income" | "expense";
    amount: string;
    description: string;
    accountName?: string;
    categoryName?: string;
  },
): Promise<void> {
  await navigateViaSidebar(page, "Transactions", "Transactions");
  await pageHeaderLink(page, "Add transaction").click();
  await page.getByRole("heading", { name: "Add transaction" }).waitFor();
  await page.getByLabel(/^type/i).selectOption(options.type);
  if (options.accountName) {
    await page.getByLabel(/^account/i).selectOption({ label: options.accountName });
  }
  if (options.categoryName) {
    await page.getByLabel(/^category/i).selectOption({ label: options.categoryName });
  }
  await page.getByLabel(/^amount/i).fill(options.amount);
  await page.getByLabel(/^description/i).fill(options.description);
  await page.getByRole("button", { name: "Save transaction" }).click();
  await page.waitForURL(`**${routes.transactions}`, { timeout: 60_000 });
}

export async function openSidebarLink(page: Page, label: string): Promise<void> {
  await openMobileNavIfNeeded(page);
  await page.getByRole("link", { name: label }).click();
}
