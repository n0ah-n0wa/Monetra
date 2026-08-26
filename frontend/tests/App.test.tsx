import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { App } from "../src/App";

vi.mock("@/api/health", () => ({
  fetchHealth: vi.fn(async () => ({ status: "ok" as const })),
}));

function renderApp() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App foundation", () => {
  it("renders the Monetra brand", async () => {
    renderApp();
    expect(screen.getByText("Monetra")).toBeInTheDocument();
    expect(await screen.findByText(/API health: ok/i)).toBeInTheDocument();
  });
});
