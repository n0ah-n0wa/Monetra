import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";

type EmptyStateProps = {
  title: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  children?: ReactNode;
};

export function EmptyState({
  title,
  description,
  actionLabel,
  actionHref,
  onAction,
  children,
}: EmptyStateProps) {
  return (
    <div className="state state--empty">
      <p className="state__title">{title}</p>
      {description ? <p className="state__description">{description}</p> : null}
      {children}
      {actionLabel && actionHref ? (
        <ButtonLink to={actionHref}>{actionLabel}</ButtonLink>
      ) : null}
      {actionLabel && onAction && !actionHref ? (
        <Button onClick={onAction}>{actionLabel}</Button>
      ) : null}
    </div>
  );
}
