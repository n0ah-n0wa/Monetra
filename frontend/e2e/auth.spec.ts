import { test, expect } from "@playwright/test";
import { loginViaUi, logoutViaUi, registerUser, registerViaUi } from "./helpers/auth";
import { routes } from "./helpers/constants";

test.describe("Authentication", () => {
  test("registers a new user", async ({ page }) => {
    await registerViaUi(page, "register");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText(/reporting in/i)).toBeVisible();
  });

  test("logs in an existing user", async ({ page, request }) => {
    const user = await registerUser(request, "login");
    await loginViaUi(page, user);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });

  test("logs out", async ({ page, request }) => {
    const user = await registerUser(request, "logout");
    await loginViaUi(page, user);
    await logoutViaUi(page);
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("redirects to login when the session expires", async ({
    page,
    context,
    request,
  }) => {
    const user = await registerUser(request, "session-expiry");
    await loginViaUi(page, user);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    await context.clearCookies();
    await page.route("**/api/v1/auth/refresh", async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "UNAUTHORIZED", message: "Session expired." },
        }),
      });
    });
    await page.route("**/api/v1/accounts**", async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "UNAUTHORIZED", message: "Session expired." },
        }),
      });
    });

    await page.getByRole("link", { name: "Accounts" }).click();
    await expect(page).toHaveURL(new RegExp(`${routes.login}$`));
    await expect(page.getByText("Session expired")).toBeVisible();
  });
});
