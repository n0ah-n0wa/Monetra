import { NavLink } from "react-router-dom";
import { NotificationUnreadBadge } from "@/features/notifications/components/NotificationUnreadBadge";
import { navItems, routes } from "@/lib/routes";
import { useMediaQuery } from "@/lib/use-media-query";
import { cn } from "@/lib/utils";

type SidebarProps = {
  open: boolean;
  onNavigate?: () => void;
};

export function Sidebar({ open, onNavigate }: SidebarProps) {
  const isMobileNav = useMediaQuery("(max-width: 900px)");

  return (
    <aside
      id="main-navigation"
      className={cn("sidebar", open && "sidebar--open")}
      aria-label="Main navigation"
      aria-hidden={isMobileNav && !open ? true : undefined}
    >
      <div className="sidebar__brand">
        <span className="sidebar__logo">Monetra</span>
        <span className="sidebar__tagline">Personal finance</span>
      </div>
      <nav className="sidebar__nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn("sidebar__link", isActive && "sidebar__link--active")
            }
            onClick={onNavigate}
            end={item.path === "/dashboard"}
          >
            <span className="sidebar__link-label">{item.label}</span>
            {item.path === routes.notifications ? <NotificationUnreadBadge /> : null}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
