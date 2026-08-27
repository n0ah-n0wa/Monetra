import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import {
  fetchNotificationPreferences,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  updateNotificationPreferences,
  type NotificationListParams,
  type NotificationPreferenceUpdatePayload,
} from "@/features/notifications/api";
import { queryKeys } from "@/lib/query-client";

export function useNotificationsQuery(
  params: NotificationListParams = { page: 1, page_size: 20 },
) {
  return useQuery({
    queryKey: queryKeys.notifications.list(params),
    queryFn: () => fetchNotifications(params),
    placeholderData: keepPreviousData,
  });
}

export function useUnreadNotificationsCountQuery() {
  return useQuery({
    queryKey: queryKeys.notifications.unreadCount,
    queryFn: () => fetchNotifications({ page: 1, page_size: 1, unread_only: true }),
    select: (data) => data.total_items,
  });
}

export function useNotificationPreferencesQuery() {
  return useQuery({
    queryKey: queryKeys.notifications.preferences,
    queryFn: fetchNotificationPreferences,
  });
}

export function useMarkNotificationReadMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useMarkAllNotificationsReadMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useUpdateNotificationPreferencesMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: NotificationPreferenceUpdatePayload) =>
      updateNotificationPreferences(payload),
    onSuccess: async (preferences) => {
      queryClient.setQueryData(queryKeys.notifications.preferences, preferences);
    },
  });
}
