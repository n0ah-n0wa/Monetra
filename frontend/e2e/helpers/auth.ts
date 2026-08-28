import { randomUUID } from "node:crypto";
import type { APIRequestContext, Page } from "@playwright/test";
import { API_PREFIX, E2E_PASSWORD, routes } from "./constants";

export type TestUser = {
  email: string;
  password: string;
  accessToken: string;
};

const NAV_OPTIONS = { waitUntil: "domcontentloaded" as const };

export function uniqueEmail(label: string): string {
  return `e2e-${label}-${randomUUID()}@example.com`;
}

export async function registerUser(
  request: APIRequestContext,
  label: string,
): Promise<TestUser> {
  const email = uniqueEmail(label);
  const response = await request.post(`${API_PREFIX}/auth/register`, {
    data: { email, password: E2E_PASSWORD },
  });
  if (!response.ok()) {
    throw new Error(`Register failed (${response.status()}): ${await response.text()}`);
  }
  const body = (await response.json()) as { access_token: string };
  return { email, password: E2E_PASSWORD, accessToken: body.access_token };
}

export async function registerViaUi(page: Page, label: string): Promise<TestUser> {
  const user = { email: uniqueEmail(label), password: E2E_PASSWORD, accessToken: "" };
  await page.goto(routes.register, NAV_OPTIONS);
  await page.getByRole("heading", { name: "Create account" }).waitFor();
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL(`**${routes.dashboard}`, { timeout: 60_000 });
  return user;
}

export async function loginViaUi(
  page: Page,
  user: Pick<TestUser, "email" | "password">,
): Promise<void> {
  await page.goto(routes.login, NAV_OPTIONS);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(`**${routes.dashboard}`, { timeout: 60_000 });
}

export async function logoutViaUi(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.waitForURL(`**${routes.login}`, { timeout: 60_000 });
}

export function authHeaders(accessToken: string): Record<string, string> {
  return { Authorization: `Bearer ${accessToken}` };
}
