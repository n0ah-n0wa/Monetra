import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/errors";
import { setAccessToken } from "@/api/client";
import { ProtectedRoute } from "@/components/routing/ProtectedRoute";
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
  fetchCurrentUser: vi.fn(),
  requestPasswordReset: vi.fn(),
  confirmPasswordReset: vi.fn(),
}));

function renderProtectedRoute() {
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
    { initialEntries: [routes.dashboard] },
  );

  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("AuthProvider session handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setAccessToken(null);
    vi.mocked(authApi.refreshSession).mockRejectedValue(new Error("no session"));
  });

  it("shows a profile error state when /users/me fails with a server error", async () => {
    setAccessToken("token");
    vi.mocked(authApi.fetchCurrentUser).mockRejectedValue(
      new ApiError("Server error", 500, {}, "INTERNAL_ERROR"),
    );

    renderProtectedRoute();

    expect(await screen.findByText("Unable to load your profile")).toBeInTheDocument();
    expect(screen.getByText("Server error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.queryByText("Protected dashboard")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(authApi.fetchCurrentUser).toHaveBeenCalled();
    });
  });
});
