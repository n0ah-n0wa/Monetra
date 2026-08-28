import { useMemo, useState } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { NotificationListItem } from "@/features/notifications/components/NotificationListItem";
import { NotificationPreferencesForm } from "@/features/notifications/components/NotificationPreferencesForm";
import {
  useMarkAllNotificationsReadMutation,
  useMarkNotificationReadMutation,
  useNotificationPreferencesQuery,
  useNotificationsQuery,
  useUnreadNotificationsCountQuery,
} from "@/features/notifications/hooks";

type ReadFilter = "all" | "unread";

export function NotificationsPage() {
  const [readFilter, setReadFilter] = useState<ReadFilter>("all");
  const [markingReadId, setMarkingReadId] = useState<string | null>(null);

  const listParams = useMemo(
    () => ({
      page: 1,
      page_size: 50,
      unread_only: readFilter === "unread",
    }),
    [readFilter],
  );

  const notificationsQuery = useNotificationsQuery(listParams);
  const unreadCountQuery = useUnreadNotificationsCountQuery();
  const preferencesQuery = useNotificationPreferencesQuery();
  const markReadMutation = useMarkNotificationReadMutation();
  const markAllReadMutation = useMarkAllNotificationsReadMutation();

  const notifications = notificationsQuery.data?.items ?? [];
  const unreadCount = unreadCountQuery.data ?? 0;
  const hasUnread = unreadCount > 0;

  async function handleMarkRead(id: string) {
    setMarkingReadId(id);
    try {
      await markReadMutation.mutateAsync(id);
    } finally {
      setMarkingReadId(null);
    }
  }

  async function handleMarkAllRead() {
    await markAllReadMutation.mutateAsync();
  }

  return (
    <PageContainer>
      <PageHeader
        title="Notifications"
        description="Stay informed about budgets, goals, imports, and recurring activity."
        actions={
          hasUnread ? (
            <Button
              type="button"
              variant="secondary"
              loading={markAllReadMutation.isPending}
              onClick={() => void handleMarkAllRead()}
            >
              Mark all as read
            </Button>
          ) : null
        }
      />

      <div className="notification-center__summary" aria-live="polite">
        {unreadCountQuery.isPending ? (
          <span className="notification-center__summary-text">
            Checking unread notifications…
          </span>
        ) : null}
        {unreadCountQuery.isSuccess ? (
          <p className="notification-center__summary-text">
            {unreadCount === 0 ? (
              "You're all caught up."
            ) : (
              <>
                <Badge variant="info" aria-hidden="true">
                  {unreadCount}
                </Badge>
                <span>
                  {unreadCount} unread notification{unreadCount === 1 ? "" : "s"}
                </span>
              </>
            )}
          </p>
        ) : null}
      </div>

      <section
        aria-labelledby="notification-inbox-heading"
        className="notification-center__inbox"
      >
        <div className="notification-center__inbox-header">
          <h2 id="notification-inbox-heading" className="import-section__title">
            Inbox
          </h2>
          <label className="toolbar__filter" htmlFor="notification-read-filter">
            <span>Show</span>
            <Select
              id="notification-read-filter"
              value={readFilter}
              onChange={(event) => setReadFilter(event.target.value as ReadFilter)}
            >
              <option value="all">All notifications</option>
              <option value="unread">Unread only</option>
            </Select>
          </label>
        </div>

        {notificationsQuery.isPending ? (
          <LoadingState title="Loading notifications" />
        ) : null}

        {notificationsQuery.isError ? (
          <ErrorState
            error={notificationsQuery.error}
            title="Unable to load notifications"
            onRetry={() => void notificationsQuery.refetch()}
          />
        ) : null}

        {notificationsQuery.isSuccess && notifications.length === 0 ? (
          <EmptyState
            title={
              readFilter === "unread" ? "No unread notifications" : "No notifications"
            }
            description={
              readFilter === "unread"
                ? "Switch to all notifications or check back later."
                : "New alerts about budgets, goals, imports, and recurring activity will appear here."
            }
          />
        ) : null}

        {notificationsQuery.isSuccess && notifications.length > 0 ? (
          <div className="notification-list" role="list" aria-label="Notifications">
            {notifications.map((notification) => (
              <div key={notification.id} role="listitem">
                <NotificationListItem
                  notification={notification}
                  markingRead={markingReadId === notification.id}
                  onMarkRead={(id) => void handleMarkRead(id)}
                />
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section
        aria-labelledby="notification-preferences-section-heading"
        className="notification-center__preferences card"
      >
        <h2 id="notification-preferences-section-heading" className="sr-only">
          Notification preferences
        </h2>

        {preferencesQuery.isPending ? (
          <LoadingState title="Loading preferences" />
        ) : null}

        {preferencesQuery.isError ? (
          <ErrorState
            error={preferencesQuery.error}
            title="Unable to load notification preferences"
            onRetry={() => void preferencesQuery.refetch()}
          />
        ) : null}

        {preferencesQuery.isSuccess ? (
          <NotificationPreferencesForm preferences={preferencesQuery.data} />
        ) : null}
      </section>
    </PageContainer>
  );
}
