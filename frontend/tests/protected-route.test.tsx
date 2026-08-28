import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { setAccessToken } from "@/api/client";
import { GuestRoute, ProtectedRoute } from "@/components/routing/ProtectedRoute";
import { Header } from "@/components/layout/Header";
import { AuthProvider } from "@/features/auth/context";
import { routes } from "@/lib/routes";
import * as authApi from "@/features/auth/api";

vi.mock("@/features/auth/api", () => ({
  refreshSession: vi.fn(async () => {
    throw new Error("no session");
  }),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(async () => undefined),
  fetchCurrentUser: vi.fn(async () => ({
    id: "user-1",
    email: "user@example.com",
    reporting_currency: "USD",
  })),
  requestPasswordReset: vi.fn(),
  confirmPasswordReset: vi.fn(),
}));

function renderProtectedRoute(initialRoute = routes.dashboard) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [{ path: routes.dashboard, element: <div>Protected dashboard</div> }],
      },
      { path: routes.login, element: <div>Login page</div> },
    ],
    { initialEntries: [initialRoute] },
  );

  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setAccessToken(null);
    vi.mocked(authApi.refreshSession).mockRejectedValue(new Error("no session"));
  });

  it("redirects guests to login", async () => {
    renderProtectedRoute();
    expect(await screen.findByText("Login page")).toBeInTheDocument();
  });

  it("renders protected content for authenticated users", async () => {
    setAccessToken("token");
    renderProtectedRoute();
    expect(await screen.findByText("Protected dashboard")).toBeInTheDocument();
    expect(authApi.fetchCurrentUser).toHaveBeenCalled();
  });
});

describe("session and logout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setAccessToken(null);
  });

  it("GuestRoute sends authenticated users to the dashboard", async () => {
    setAccessToken("token");
    vi.mocked(authApi.refreshSession).mockResolvedValue({
      access_token: "token",
      token_type: "bearer",
      expires_in: 900,
    });

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const router = createMemoryRouter(
      [
        {
          element: <GuestRoute />,
          children: [{ path: routes.login, element: <div>Login form</div> }],
        },
        { path: routes.dashboard, element: <div>Dashboard home</div> },
      ],
      { initialEntries: [routes.login] },
    );

    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Dashboard home")).toBeInTheDocument();
  });

  it("logs out and returns to login", async () => {
    const user = userEvent.setup();
    setAccessToken("token");
    vi.mocked(authApi.refreshSession).mockResolvedValue({
      access_token: "token",
      token_type: "bearer",
      expires_in: 900,
    });

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const router = createMemoryRouter(
      [
        {
          path: routes.dashboard,
          element: (
            <div>
              <Header sidebarOpen={false} onMenuToggle={() => undefined} />
              <div>Dashboard body</div>
            </div>
          ),
        },
        { path: routes.login, element: <div>Signed out login</div> },
      ],
      { initialEntries: [routes.dashboard] },
    );

    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Dashboard body")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /sign out/i }));

    await waitFor(() => {
      expect(screen.getByText("Signed out login")).toBeInTheDocument();
    });
    expect(authApi.logout).toHaveBeenCalled();
  });
});
