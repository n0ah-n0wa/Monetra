import { useEffect, type ReactNode } from "react";
import { Link } from "react-router-dom";

type AuthLayoutProps = {
  children: ReactNode;
  title?: string;
  pageTitle?: string;
};

export function AuthLayout({ children, title, pageTitle }: AuthLayoutProps) {
  useEffect(() => {
    if (!pageTitle) {
      return;
    }
    document.title = `${pageTitle} · Monetra`;
    return () => {
      document.title = "Monetra";
    };
  }, [pageTitle]);

  return (
    <div className="auth-layout">
      <div className="auth-layout__panel">
        <header className="auth-layout__header">
          <Link to="/login" className="auth-layout__brand" aria-label="Monetra home">
            Monetra
          </Link>
          {pageTitle ? <h1 className="sr-only">{pageTitle}</h1> : null}
          {title ? <p className="auth-layout__subtitle">{title}</p> : null}
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
