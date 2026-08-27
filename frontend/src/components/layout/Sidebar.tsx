import { NavLink } from "react-router-dom";
import { navItems } from "@/lib/routes";
import { cn } from "@/lib/utils";

type SidebarProps = {
  open: boolean;
  onNavigate?: () => void;
};

export function Sidebar({ open, onNavigate }: SidebarProps) {
  return (
    <aside
      id="main-navigation"
      className={cn("sidebar", open && "sidebar--open")}
      aria-label="Main navigation"
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
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
