import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { Modal } from "@/components/ui/Modal";
import { AuthProvider } from "@/features/auth/context";
import { setAccessToken } from "@/api/client";
import { renderWithAuth } from "./test-utils";

vi.mock("@/features/auth/api", () => ({
  refreshSession: vi.fn(async () => ({
    access_token: "token",
    token_type: "bearer",
    expires_in: 900,
  })),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  fetchCurrentUser: vi.fn(async () => ({
    id: "user-1",
    email: "user@example.com",
    reporting_currency: "USD",
  })),
  requestPasswordReset: vi.fn(),
  confirmPasswordReset: vi.fn(),
}));

describe("Modal accessibility", () => {
  it("exposes dialog semantics and closes with Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <Modal open title="Delete account" description="This cannot be undone." onClose={onClose}>
        <button type="button">Confirm</button>
      </Modal>,
    );

    const dialog = screen.getByRole("dialog", { name: "Delete account" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAttribute("aria-describedby");

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("keeps keyboard focus inside the dialog", async () => {
    const user = userEvent.setup();

    render(
      <Modal open title="Edit budget" onClose={() => undefined}>
        <button type="button">First action</button>
        <button type="button">Second action</button>
      </Modal>,
    );

    const firstAction = screen.getByRole("button", { name: "First action" });
    const closeButton = screen.getByRole("button", { name: "Close" });

    expect(closeButton).toHaveFocus();

    await user.tab();
    expect(firstAction).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("button", { name: "Second action" })).toHaveFocus();

    await user.tab();
    expect(closeButton).toHaveFocus();
  });
});

describe("application shell accessibility", () => {
  it("renders a skip link to main content", () => {
    setAccessToken("test-access-token");
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const router = createMemoryRouter(
      [
        {
          element: <AppShell />,
          children: [{ path: "/dashboard", element: <div>Dashboard</div> }],
        },
      ],
      { initialEntries: ["/dashboard"] },
    );

    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>,
    );

    const skipLink = screen.getByRole("link", { name: /skip to main content/i });
    expect(skipLink).toHaveAttribute("href", "#main-content");
    expect(document.getElementById("main-content")).toBeInTheDocument();
  });

  it("announces signed-in user email to screen readers", async () => {
    renderWithAuth(
      <Header sidebarOpen={false} onMenuToggle={() => undefined} />,
      {
        authenticated: true,
        initialEntries: ["/"],
        routes: [
          {
            path: "*",
            element: <Header sidebarOpen={false} onMenuToggle={() => undefined} />,
          },
        ],
      },
    );

    expect(await screen.findByText(/signed in as/i)).toBeInTheDocument();
    expect(await screen.findByText("user@example.com")).toBeInTheDocument();
  });
});
