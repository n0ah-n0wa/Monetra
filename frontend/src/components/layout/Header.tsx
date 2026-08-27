import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/hooks";

type HeaderProps = {
  onMenuToggle: () => void;
};

export function Header({ onMenuToggle }: HeaderProps) {
  const { user, logout, isLoggingOut } = useAuth();

  return (
    <header className="app-header">
      <div className="app-header__start">
        <Button variant="ghost" size="sm" onClick={onMenuToggle} aria-label="Toggle navigation menu">
          Menu
        </Button>
        <span className="app-header__title">Monetra</span>
      </div>
      <div className="app-header__end">
        {user ? <span className="app-header__user">{user.email}</span> : null}
        <Button variant="secondary" size="sm" loading={isLoggingOut} onClick={() => void logout()}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
