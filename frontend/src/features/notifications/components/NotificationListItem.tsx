import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  formatNotificationTimestamp,
  formatNotificationType,
  notificationTypeVariant,
  type Notification,
} from "@/features/notifications/api";

type NotificationListItemProps = {
  notification: Notification;
  markingRead?: boolean;
  onMarkRead: (id: string) => void;
};

export function NotificationListItem({
  notification,
  markingRead = false,
  onMarkRead,
}: NotificationListItemProps) {
  return (
    <article
      className={[
        "notification-item",
        notification.is_read ? "notification-item--read" : "notification-item--unread",
      ].join(" ")}
      aria-labelledby={`notification-title-${notification.id}`}
    >
      <div className="notification-item__main">
        <div className="notification-item__title-row">
          {!notification.is_read ? (
            <span className="notification-item__unread-dot" aria-hidden="true" />
          ) : null}
          <h3
            id={`notification-title-${notification.id}`}
            className="notification-item__title"
          >
            {notification.title}
          </h3>
          <Badge variant={notificationTypeVariant(notification.notification_type)}>
            {formatNotificationType(notification.notification_type)}
          </Badge>
        </div>
        <p className="notification-item__message">{notification.message}</p>
        <p className="notification-item__meta">
          <time dateTime={notification.created_at}>
            {formatNotificationTimestamp(notification.created_at)}
          </time>
          {notification.is_read && notification.read_at ? (
            <> · Read {formatNotificationTimestamp(notification.read_at)}</>
          ) : null}
        </p>
      </div>
      {!notification.is_read ? (
        <div className="notification-item__actions">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            loading={markingRead}
            onClick={() => onMarkRead(notification.id)}
          >
            Mark as read
          </Button>
        </div>
      ) : null}
    </article>
  );
}
