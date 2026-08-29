import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { routes } from "@/lib/routes";
import { renderWithAuth } from "./test-utils";
import { ApiError } from "@/api/errors";
import * as authApi from "@/features/auth/api";

vi.mock("@/features/auth/api", () => ({
  refreshSession: vi.fn(async () => {
    throw new Error("no session");
  }),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  fetchCurrentUser: vi.fn(),
  requestPasswordReset: vi.fn(),
  confirmPasswordReset: vi.fn(),
}));

describe("auth pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authApi.refreshSession).mockRejectedValue(new Error("no session"));
  });

  it("renders login form after bootstrap", async () => {
    renderWithAuth(<LoginPage />, {
      routes: [
        { path: routes.login, element: <LoginPage /> },
        { path: routes.dashboard, element: <div>Dashboard</div> },
      ],
      initialEntries: [routes.login],
    });

    expect(
      await screen.findByRole("heading", { name: /sign in/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
  });

  it("shows client-side validation errors on empty login submit", async () => {
    const user = userEvent.setup();
    renderWithAuth(<LoginPage />, {
      routes: [{ path: routes.login, element: <LoginPage /> }],
      initialEntries: [routes.login],
    });

    await screen.findByRole("heading", { name: /sign in/i });
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/enter a valid email address/i)).toBeInTheDocument();
    expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    expect(authApi.login).not.toHaveBeenCalled();
  });

  it("submits login and navigates to dashboard", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "token",
      token_type: "bearer",
      expires_in: 900,
    });
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue({
      id: "user-1",
      email: "user@example.com",
      reporting_currency: "USD",
    });

    renderWithAuth(<LoginPage />, {
      routes: [
        { path: routes.login, element: <LoginPage /> },
        { path: routes.dashboard, element: <div>Dashboard ready</div> },
      ],
      initialEntries: [routes.login],
    });

    await screen.findByRole("heading", { name: /sign in/i });
    await user.type(screen.getByLabelText(/^email/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password/i), "Password1");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Dashboard ready")).toBeInTheDocument();
    expect(authApi.login).toHaveBeenCalledWith(
      {
        email: "user@example.com",
        password: "Password1",
      },
      expect.anything(),
    );
  });

  it("displays API errors on failed login", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockRejectedValue(
      new ApiError("Invalid email or password.", 401, {}, "INVALID_CREDENTIALS"),
    );

    renderWithAuth(<LoginPage />, {
      routes: [{ path: routes.login, element: <LoginPage /> }],
      initialEntries: [routes.login],
    });

    await screen.findByRole("heading", { name: /sign in/i });
    await user.type(screen.getByLabelText(/^email/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password/i), "wrong");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/invalid email or password/i)).toBeInTheDocument();
  });

  it("maps registration field errors from the API", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.register).mockRejectedValue(
      new ApiError(
        "Unable to complete registration. Please try again or sign in.",
        409,
        {},
        "REGISTRATION_FAILED",
      ),
    );

    renderWithAuth(<RegisterPage />, {
      routes: [{ path: routes.register, element: <RegisterPage /> }],
      initialEntries: [routes.register],
    });

    await screen.findByRole("heading", { name: /create account/i });
    await user.type(screen.getByLabelText(/^email/i), "taken@example.com");
    await user.type(screen.getByLabelText(/^password/i), "Password1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to complete registration. Please try again or sign in.",
    );
  });

  it("shows forgot-password success acknowledgement", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.requestPasswordReset).mockResolvedValue({
      message: "If an account exists, reset instructions were sent.",
    });

    renderWithAuth(<ForgotPasswordPage />, {
      routes: [{ path: routes.forgotPassword, element: <ForgotPasswordPage /> }],
      initialEntries: [routes.forgotPassword],
    });

    await screen.findByRole("heading", { name: /forgot password/i });
    await user.type(screen.getByLabelText(/^email/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByText(/reset requested/i)).toBeInTheDocument();
  });

  it("validates matching passwords on reset form", async () => {
    const user = userEvent.setup();
    renderWithAuth(<ResetPasswordPage />, {
      routes: [{ path: routes.resetPassword, element: <ResetPasswordPage /> }],
      initialEntries: [`${routes.resetPassword}?token=abc`],
    });

    await screen.findByRole("heading", { name: /reset password/i });
    expect(screen.getByLabelText(/reset token/i)).toHaveValue("abc");
    await user.type(screen.getByLabelText(/^new password/i), "Password1");
    await user.type(screen.getByLabelText(/confirm password/i), "Password2");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByText(/passwords must match/i)).toBeInTheDocument();
    expect(authApi.confirmPasswordReset).not.toHaveBeenCalled();
  });

  it("shows session expired banner on login", async () => {
    renderWithAuth(<LoginPage />, {
      routes: [{ path: routes.login, element: <LoginPage /> }],
      initialEntries: [
        {
          pathname: routes.login,
          state: { reason: "session-expired" },
        },
      ],
    });

    expect(await screen.findByText(/session expired/i)).toBeInTheDocument();
  });
});

describe("auth schemas integration", () => {
  it("keeps loading state while login request is in flight", async () => {
    const user = userEvent.setup();
    let resolveLogin: (value: {
      access_token: string;
      token_type: string;
      expires_in: number;
    }) => void = () => undefined;

    vi.mocked(authApi.login).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveLogin = resolve;
        }),
    );

    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue({
      id: "user-1",
      email: "user@example.com",
      reporting_currency: "USD",
    });

    renderWithAuth(<LoginPage />, {
      routes: [
        { path: routes.login, element: <LoginPage /> },
        { path: routes.dashboard, element: <div>Dashboard ready</div> },
      ],
      initialEntries: [routes.login],
    });

    await screen.findByRole("heading", { name: /sign in/i });
    await user.type(screen.getByLabelText(/^email/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password/i), "Password1");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByRole("button", { name: /sign in/i })).toHaveAttribute(
      "aria-busy",
      "true",
    );

    resolveLogin({
      access_token: "token",
      token_type: "bearer",
      expires_in: 900,
    });

    expect(await screen.findByText("Dashboard ready")).toBeInTheDocument();
  });
});
