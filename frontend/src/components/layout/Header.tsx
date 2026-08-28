import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { NotificationNavLink } from "@/features/notifications/components/NotificationUnreadBadge";
import { useAuth } from "@/features/auth/hooks";
import { useMediaQuery } from "@/lib/use-media-query";
import { routes } from "@/lib/routes";

type HeaderProps = {
  sidebarOpen: boolean;
  onMenuToggle: () => void;
};

export function Header({ sidebarOpen, onMenuToggle }: HeaderProps) {
  const navigate = useNavigate();
  const { user, logout, isLoggingOut } = useAuth();
  const isMobileNav = useMediaQuery("(max-width: 900px)");

  async function handleLogout() {
    await logout();
    navigate(routes.login, { replace: true });
  }

  return (
    <header className="app-header">
      <div className="app-header__start">
        <Button
          className="app-header__menu"
          variant="ghost"
          size="sm"
          onClick={onMenuToggle}
          aria-label="Toggle navigation menu"
          aria-controls="main-navigation"
          aria-expanded={isMobileNav ? sidebarOpen : undefined}
        >
          Menu
        </Button>
        <span className="app-header__title">Monetra</span>
      </div>
      <div className="app-header__end">
        <NotificationNavLink className="app-header__notifications" />
        {user ? (
          <span className="app-header__user">
            <span className="sr-only">Signed in as </span>
            {user.email}
          </span>
        ) : null}
        <Button
          variant="secondary"
          size="sm"
          loading={isLoggingOut}
          onClick={() => void handleLogout()}
        >
          Sign out
        </Button>
      </div>
    </header>
  );
}
