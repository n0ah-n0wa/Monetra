import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "@/components/routing/ProtectedRoute";
import { AuthProvider } from "@/features/auth/context";
import { routes } from "@/lib/routes";
import { setAccessToken } from "@/api/client";
import * as authApi from "@/features/auth/api";

vi.mock("@/features/auth/api", () => ({
  refreshSession: vi.fn(async () => {
    throw new Error("no session");
  }),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  fetchCurrentUser: vi.fn(async () => ({
    id: "user-1",
    email: "user@example.com",
    reporting_currency: "USD",
  })),
}));

function renderProtectedRoute(initialRoute = routes.dashboard) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
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
  it("redirects guests to login", async () => {
    setAccessToken(null);
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
