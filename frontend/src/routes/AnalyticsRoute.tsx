import { lazy, Suspense } from "react";
import { LoadingState } from "@/components/states/LoadingState";

const AnalyticsPage = lazy(() =>
  import("@/features/analytics/pages/AnalyticsPage").then((module) => ({
    default: module.AnalyticsPage,
  })),
);

export function AnalyticsRoute() {
  return (
    <Suspense fallback={<LoadingState title="Loading analytics" />}>
      <AnalyticsPage />
    </Suspense>
  );
}
