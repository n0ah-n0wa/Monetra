import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GoalsPage } from "@/features/goals/pages/GoalsPage";
import type { Goal } from "@/features/goals/api";
import * as goalsApi from "@/features/goals/api";
import { routes } from "@/lib/routes";
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

vi.mock("@/features/goals/api", async () => {
  const actual =
    await vi.importActual<typeof import("@/features/goals/api")>(
      "@/features/goals/api",
    );
  return {
    ...actual,
    fetchGoals: vi.fn(),
    createGoal: vi.fn(),
    updateGoal: vi.fn(),
    archiveGoal: vi.fn(),
  };
});

vi.mock("@/features/accounts/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/accounts/api")>(
    "@/features/accounts/api",
  );
  return {
    ...actual,
    fetchAccounts: vi.fn(async () => ({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    })),
  };
});

const vacationGoal: Goal = {
  id: "goal-1",
  name: "Vacation",
  target_amount: "1000.0000",
  current_amount: "250.0000",
  currency: "USD",
  target_date: "2026-12-31",
  linked_account_id: null,
  status: "active",
  archived_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  progress: {
    as_of_date: "2026-01-15",
    remaining_amount: "750.0000",
    completion_percentage: "25.0000",
    required_average_contribution: "2.5000",
    average_contribution_rate: null,
    projected_completion_date: "2027-06-01",
    target_date_achievable: false,
  },
};

function renderGoals() {
  return renderWithAuth(<GoalsPage />, {
    authenticated: true,
    initialEntries: [routes.goals],
    routes: [{ path: routes.goals, element: <GoalsPage /> }],
  });
}

describe("GoalsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists goals with progress metrics", async () => {
    vi.mocked(goalsApi.fetchGoals).mockResolvedValue({
      items: [vacationGoal],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });

    renderGoals();

    expect(await screen.findByText("Vacation")).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("Active");
    expect(screen.getByText("$1,000.00")).toBeInTheDocument();
    expect(screen.getByText("$250.00")).toBeInTheDocument();
    expect(screen.getByText("$750.00")).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByText(/projection:/i)).toBeInTheDocument();
  });

  it("validates goal creation form", async () => {
    const user = userEvent.setup();
    vi.mocked(goalsApi.fetchGoals).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });

    renderGoals();
    await screen.findByText(/no goals yet/i);

    await user.click(screen.getByRole("button", { name: /^add goal$/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /create goal/i }));
    expect(await screen.findByText(/goal name is required/i)).toBeInTheDocument();
  });

  it("creates a goal", async () => {
    const user = userEvent.setup();
    vi.mocked(goalsApi.fetchGoals).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
    });
    vi.mocked(goalsApi.createGoal).mockResolvedValue(vacationGoal);

    renderGoals();
    await screen.findByText(/no goals yet/i);

    await user.click(screen.getByRole("button", { name: /^add goal$/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/^name/i), "Vacation");
    await user.type(within(dialog).getByLabelText(/^target amount/i), "1000");
    await user.click(within(dialog).getByRole("button", { name: /create goal/i }));

    await waitFor(() => {
      expect(goalsApi.createGoal).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Vacation",
          target_amount: "1000",
          currency: "USD",
          current_amount: "0",
        }),
      );
    });
  });

  it("edits a goal", async () => {
    const user = userEvent.setup();
    vi.mocked(goalsApi.fetchGoals).mockResolvedValue({
      items: [vacationGoal],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(goalsApi.updateGoal).mockResolvedValue({
      ...vacationGoal,
      name: "Trip",
    });

    renderGoals();
    await screen.findByText("Vacation");

    await user.click(screen.getByRole("button", { name: /^edit$/i }));
    const dialog = await screen.findByRole("dialog");
    const nameInput = within(dialog).getByLabelText(/^name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Trip");
    await user.click(within(dialog).getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(goalsApi.updateGoal).toHaveBeenCalledWith(
        "goal-1",
        expect.objectContaining({ name: "Trip" }),
      );
    });
  });

  it("archives a goal after confirmation", async () => {
    const user = userEvent.setup();
    vi.mocked(goalsApi.fetchGoals).mockResolvedValue({
      items: [vacationGoal],
      page: 1,
      page_size: 100,
      total_items: 1,
      total_pages: 1,
    });
    vi.mocked(goalsApi.archiveGoal).mockResolvedValue({
      ...vacationGoal,
      status: "archived",
      archived_at: "2026-02-01T00:00:00Z",
    });

    renderGoals();
    await screen.findByText("Vacation");

    await user.click(screen.getByRole("button", { name: /^archive$/i }));
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByRole("heading", { name: /archive goal\?/i }),
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /archive goal/i }));

    await waitFor(() => {
      expect(goalsApi.archiveGoal).toHaveBeenCalledWith("goal-1");
    });
  });
});
