import type { ReactNode } from "react";
import { Spinner } from "@/components/ui/Spinner";

type LoadingStateProps = {
  title?: string;
  description?: string;
  children?: ReactNode;
};

export function LoadingState({
  title = "Loading",
  description = "Fetching the latest data…",
  children,
}: LoadingStateProps) {
  return (
    <div className="state state--loading" role="status" aria-live="polite">
      <Spinner />
      <p className="state__title">{title}</p>
      <p className="state__description">{description}</p>
      {children}
    </div>
  );
}
