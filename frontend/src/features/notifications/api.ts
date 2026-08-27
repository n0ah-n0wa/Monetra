import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export type Notification = {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  is_read: boolean;
  read_at: string | null;
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

export type NotificationListParams = {
  page?: number;
  page_size?: number;
  is_read?: boolean;
};

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

export async function markNotificationRead(id: string): Promise<Notification> {
  return apiClient.post<Notification>(`/notifications/${id}/read`);
}

export async function markAllNotificationsRead(): Promise<{ updated_count: number }> {
  return apiClient.post<{ updated_count: number }>("/notifications/read-all");
}
