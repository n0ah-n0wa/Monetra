import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Header } from "@/components/layout/Header";
import type {
  Notification,
  NotificationPreferences,
} from "@/features/notifications/api";
import * as notificationsApi from "@/features/notifications/api";
import { NotificationsPage } from "@/features/notifications/pages/NotificationsPage";
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

vi.mock("@/features/notifications/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/notifications/api")>(
    "@/features/notifications/api",
  );
  return {
    ...actual,
    fetchNotifications: vi.fn(),
    fetchNotificationPreferences: vi.fn(),
    markNotificationRead: vi.fn(),
    markAllNotificationsRead: vi.fn(),
    updateNotificationPreferences: vi.fn(),
  };
});

const defaultPreferences: NotificationPreferences = {
  budget_warning_enabled: true,
  budget_exceeded_enabled: true,
  recurring_executed_enabled: true,
  goal_milestone_enabled: true,
  import_completed_enabled: true,
  import_failed_enabled: true,
  email_enabled: false,
  updated_at: "2026-02-01T00:00:00Z",
};

const unreadNotification: Notification = {
  id: "notif-1",
  notification_type: "budget_warning",
  title: "Budget nearing limit",
  message: "Groceries budget is at 85% utilization.",
  is_read: false,
  read_at: null,
  metadata: null,
  created_at: "2026-02-01T10:00:00Z",
  updated_at: "2026-02-01T10:00:00Z",
};

const readNotification: Notification = {
  id: "notif-2",
  notification_type: "import_completed",
  title: "Import completed",
  message: "5 transactions were imported.",
  is_read: true,
  read_at: "2026-02-01T11:00:00Z",
  metadata: null,
  created_at: "2026-02-01T09:00:00Z",
  updated_at: "2026-02-01T11:00:00Z",
};

function mockNotificationQueries({
  items = [unreadNotification, readNotification],
  unreadCount = 1,
  preferences = defaultPreferences,
}: {
  items?: Notification[];
  unreadCount?: number;
  preferences?: NotificationPreferences;
} = {}) {
  vi.mocked(notificationsApi.fetchNotifications).mockImplementation(async (params) => {
    if (params?.unread_only) {
      const unreadItems = items.filter((item) => !item.is_read);
      return {
        items: unreadItems.slice(0, params.page_size ?? 1),
        page: 1,
        page_size: params.page_size ?? 1,
        total_items: unreadCount,
        total_pages: unreadCount > 0 ? 1 : 0,
      };
    }
    const filtered = params?.unread_only
      ? items.filter((item) => !item.is_read)
      : items;
    return {
      items: filtered,
      page: 1,
      page_size: params?.page_size ?? 50,
      total_items: filtered.length,
      total_pages: filtered.length > 0 ? 1 : 0,
    };
  });
  vi.mocked(notificationsApi.fetchNotificationPreferences).mockResolvedValue(
    preferences,
  );
}

function renderNotificationsPage() {
  return renderWithAuth(<NotificationsPage />, {
    authenticated: true,
    initialEntries: [routes.notifications],
    routes: [{ path: routes.notifications, element: <NotificationsPage /> }],
  });
}

describe("NotificationsPage", () => {
  beforeEach(() => {
    vi.mocked(notificationsApi.markNotificationRead).mockReset();
    vi.mocked(notificationsApi.markAllNotificationsRead).mockReset();
    vi.mocked(notificationsApi.updateNotificationPreferences).mockReset();
    mockNotificationQueries();
  });

  it("renders notification list with unread count and preferences", async () => {
    renderNotificationsPage();

    expect(
      await screen.findByRole("heading", { name: "Notifications" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("1 unread notification")).toBeInTheDocument();
    expect(screen.getByText("Budget nearing limit")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Import completed" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Inbox" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /budget warnings/i })).toBeChecked();
  });

  it("shows empty state when there are no notifications", async () => {
    mockNotificationQueries({ items: [], unreadCount: 0 });
    renderNotificationsPage();

    expect(await screen.findByText("No notifications")).toBeInTheDocument();
    expect(screen.getByText(/you're all caught up/i)).toBeInTheDocument();
  });

  it("marks a notification as read", async () => {
    const user = userEvent.setup();
    vi.mocked(notificationsApi.markNotificationRead).mockResolvedValue({
      ...unreadNotification,
      is_read: true,
      read_at: "2026-02-01T12:00:00Z",
    });

    renderNotificationsPage();
    await screen.findByText("Budget nearing limit");

    await user.click(screen.getByRole("button", { name: /mark as read/i }));

    await waitFor(() => {
      expect(notificationsApi.markNotificationRead).toHaveBeenCalledWith("notif-1");
    });
  });

  it("marks all notifications as read", async () => {
    const user = userEvent.setup();
    vi.mocked(notificationsApi.markAllNotificationsRead).mockResolvedValue({
      updated_count: 1,
    });

    renderNotificationsPage();
    await screen.findByRole("button", { name: /mark all as read/i });

    await user.click(screen.getByRole("button", { name: /mark all as read/i }));

    await waitFor(() => {
      expect(notificationsApi.markAllNotificationsRead).toHaveBeenCalled();
    });
  });

  it("updates notification preferences", async () => {
    const user = userEvent.setup();
    vi.mocked(notificationsApi.updateNotificationPreferences).mockResolvedValue({
      ...defaultPreferences,
      email_enabled: true,
    });

    renderNotificationsPage();
    await screen.findByRole("checkbox", { name: /email delivery/i });

    await user.click(screen.getByRole("checkbox", { name: /email delivery/i }));
    await user.click(screen.getByRole("button", { name: /save preferences/i }));

    await waitFor(() => {
      expect(notificationsApi.updateNotificationPreferences).toHaveBeenCalledWith({
        email_enabled: true,
      });
    });

    expect(await screen.findByText(/preferences saved/i)).toBeInTheDocument();
  });

  it("filters to unread notifications only", async () => {
    const user = userEvent.setup();
    renderNotificationsPage();
    await screen.findByText("Budget nearing limit");

    await user.selectOptions(screen.getByRole("combobox", { name: /show/i }), "unread");

    await waitFor(() => {
      expect(notificationsApi.fetchNotifications).toHaveBeenCalledWith(
        expect.objectContaining({ unread_only: true }),
      );
    });
  });
});

describe("Notification unread badge", () => {
  beforeEach(() => {
    mockNotificationQueries({ unreadCount: 3 });
  });

  it("shows unread count in the header link", async () => {
    renderWithAuth(<Header onMenuToggle={() => undefined} />, {
      authenticated: true,
      initialEntries: ["/"],
      routes: [{ path: "*", element: <Header onMenuToggle={() => undefined} /> }],
    });

    const link = await screen.findByRole("link", { name: /notifications, 3 unread/i });
    expect(within(link).getByLabelText("3 unread notifications")).toBeInTheDocument();
  });
});
