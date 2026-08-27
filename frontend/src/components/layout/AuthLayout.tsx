import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type AuthLayoutProps = {
  children: ReactNode;
  title?: string;
};

export function AuthLayout({ children, title }: AuthLayoutProps) {
  return (
    <div className="auth-layout">
      <div className="auth-layout__panel">
        <header className="auth-layout__header">
          <Link to="/login" className="auth-layout__brand" aria-label="Monetra home">
            Monetra
          </Link>
          {title ? <p className="auth-layout__subtitle">{title}</p> : null}
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
