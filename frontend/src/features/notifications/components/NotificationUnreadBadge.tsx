import { Link } from "react-router-dom";
import { useUnreadNotificationsCountQuery } from "@/features/notifications/hooks";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

type NotificationUnreadBadgeProps = {
  className?: string;
  showZero?: boolean;
};

export function NotificationUnreadBadge({
  className,
  showZero = false,
}: NotificationUnreadBadgeProps) {
  const unreadQuery = useUnreadNotificationsCountQuery();
  const count = unreadQuery.data ?? 0;

  if (!showZero && (unreadQuery.isPending || count === 0)) {
    return null;
  }

  return (
    <span
      className={cn("notification-unread-badge", className)}
      aria-label={`${count} unread notifications`}
    >
      {count > 99 ? "99+" : count}
    </span>
  );
}

type NotificationNavLinkProps = {
  className?: string;
  onNavigate?: () => void;
};

export function NotificationNavLink({
  className,
  onNavigate,
}: NotificationNavLinkProps) {
  const unreadQuery = useUnreadNotificationsCountQuery();
  const count = unreadQuery.data ?? 0;

  return (
    <Link
      to={routes.notifications}
      className={cn("notification-nav-link", className)}
      onClick={onNavigate}
      aria-label={count > 0 ? `Notifications, ${count} unread` : "Notifications"}
    >
      <span aria-hidden="true">Notifications</span>
      <NotificationUnreadBadge />
    </Link>
  );
}
