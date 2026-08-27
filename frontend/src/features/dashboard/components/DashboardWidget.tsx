import type { ReactNode } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { DashboardSkeleton } from "@/features/dashboard/components/DashboardSkeleton";
import { cn } from "@/lib/utils";

type DashboardWidgetProps = {
  title: string;
  description?: string;
  isLoading?: boolean;
  isError?: boolean;
  error?: unknown;
  onRetry?: () => void;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  skeletonLines?: number;
  className?: string;
  children: ReactNode;
};

export function DashboardWidget({
  title,
  description,
  isLoading = false,
  isError = false,
  error,
  onRetry,
  isEmpty = false,
  emptyTitle = "No data yet",
  emptyDescription,
  skeletonLines = 3,
  className,
  children,
}: DashboardWidgetProps) {
  return (
    <Card className={cn("dashboard-widget", className)}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {isLoading ? <DashboardSkeleton lines={skeletonLines} /> : null}
        {isError ? (
          <ErrorState error={error} title="Unable to load" onRetry={onRetry} />
        ) : null}
        {!isLoading && !isError && isEmpty ? (
          <EmptyState title={emptyTitle} description={emptyDescription} />
        ) : null}
        {!isLoading && !isError && !isEmpty ? children : null}
      </CardContent>
    </Card>
  );
}

type DashboardStatCardProps = {
  label: string;
  value: ReactNode;
  hint?: string;
  isLoading?: boolean;
  isError?: boolean;
  error?: unknown;
  onRetry?: () => void;
};

export function DashboardStatCard({
  label,
  value,
  hint,
  isLoading = false,
  isError = false,
  error,
  onRetry,
}: DashboardStatCardProps) {
  return (
    <Card className="dashboard-stat" aria-busy={isLoading}>
      <CardContent>
        {isLoading ? <DashboardSkeleton lines={2} compact /> : null}
        {isError ? (
          <ErrorState error={error} title="Unavailable" onRetry={onRetry} />
        ) : null}
        {!isLoading && !isError ? (
          <>
            <p className="dashboard-stat__label">{label}</p>
            <p className="dashboard-stat__value">{value}</p>
            {hint ? <p className="dashboard-stat__hint">{hint}</p> : null}
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
