import type { ReactNode } from "react";
import { DashboardWidget } from "@/features/dashboard/components/DashboardWidget";

type AnalyticsChartPanelProps = {
  title: string;
  description?: string;
  isLoading?: boolean;
  isError?: boolean;
  error?: unknown;
  onRetry?: () => void;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  children: ReactNode;
  table: ReactNode;
};

export function AnalyticsChartPanel({
  title,
  description,
  isLoading = false,
  isError = false,
  error,
  onRetry,
  isEmpty = false,
  emptyTitle = "No data for this period",
  emptyDescription,
  children,
  table,
}: AnalyticsChartPanelProps) {
  return (
    <DashboardWidget
      title={title}
      description={description}
      isLoading={isLoading}
      isError={isError}
      error={error}
      onRetry={onRetry}
      isEmpty={isEmpty}
      emptyTitle={emptyTitle}
      emptyDescription={emptyDescription}
      skeletonLines={5}
      className="analytics-panel"
    >
      <div className="analytics-panel__chart" aria-hidden="true">
        {children}
      </div>
      <div className="analytics-panel__table">{table}</div>
    </DashboardWidget>
  );
}
