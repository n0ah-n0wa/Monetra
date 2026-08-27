import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export const NOTIFICATION_TYPES = [
  "budget_warning",
  "budget_exceeded",
  "recurring_created",
  "goal_milestone",
  "import_completed",
  "import_failed",
  "general",
] as const;

export type NotificationType = (typeof NOTIFICATION_TYPES)[number];

export type Notification = {
  id: string;
  notification_type: NotificationType | string;
  title: string;
  message: string;
  is_read: boolean;
  read_at: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type NotificationPreferences = {
  budget_warning_enabled: boolean;
  budget_exceeded_enabled: boolean;
  recurring_executed_enabled: boolean;
  goal_milestone_enabled: boolean;
  import_completed_enabled: boolean;
  import_failed_enabled: boolean;
  email_enabled: boolean;
  updated_at: string;
};

export type NotificationPreferenceUpdatePayload = Partial<
  Pick<
    NotificationPreferences,
    | "budget_warning_enabled"
    | "budget_exceeded_enabled"
    | "recurring_executed_enabled"
    | "goal_milestone_enabled"
    | "import_completed_enabled"
    | "import_failed_enabled"
    | "email_enabled"
  >
>;

export type NotificationListParams = {
  page?: number;
  page_size?: number;
  unread_only?: boolean;
};

export function formatNotificationType(type: string): string {
  const labels: Record<string, string> = {
    budget_warning: "Budget warning",
    budget_exceeded: "Budget exceeded",
    recurring_created: "Recurring transaction",
    goal_milestone: "Goal milestone",
    import_completed: "Import completed",
    import_failed: "Import failed",
    general: "General",
  };
  return labels[type] ?? type.replaceAll("_", " ");
}

export function notificationTypeVariant(
  type: string,
): "success" | "warning" | "info" | "neutral" {
  if (type === "import_completed" || type === "goal_milestone") {
    return "success";
  }
  if (
    type === "budget_warning" ||
    type === "budget_exceeded" ||
    type === "import_failed"
  ) {
    return "warning";
  }
  if (type === "recurring_created") {
    return "info";
  }
  return "neutral";
}

export function formatNotificationTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export async function fetchNotifications(
  params: NotificationListParams = {},
): Promise<PaginatedResponse<Notification>> {
  return apiClient.get<PaginatedResponse<Notification>>(
    `/notifications${toSearchParams(params)}`,
  );
}

export async function fetchNotificationPreferences(): Promise<NotificationPreferences> {
  return apiClient.get<NotificationPreferences>("/notifications/preferences");
}

export async function updateNotificationPreferences(
  payload: NotificationPreferenceUpdatePayload,
): Promise<NotificationPreferences> {
  return apiClient.patch<NotificationPreferences>(
    "/notifications/preferences",
    payload,
  );
}

export async function markNotificationRead(id: string): Promise<Notification> {
  return apiClient.post<Notification>(`/notifications/${id}/read`);
}

export async function markAllNotificationsRead(): Promise<{ updated_count: number }> {
  return apiClient.post<{ updated_count: number }>("/notifications/read-all");
}
