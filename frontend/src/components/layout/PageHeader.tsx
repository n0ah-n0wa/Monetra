import { useEffect, type ReactNode } from "react";

type PageHeaderProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
};

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  useEffect(() => {
    document.title = `${title} · Monetra`;
    return () => {
      document.title = "Monetra";
    };
  }, [title]);

  return (
    <header className="page-header">
      <div className="page-header__content">
        <h1>{title}</h1>
        {description ? <p className="page-header__description">{description}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}
