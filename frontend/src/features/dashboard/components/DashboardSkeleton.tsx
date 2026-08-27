import { cn } from "@/lib/utils";

type DashboardSkeletonProps = {
  lines?: number;
  compact?: boolean;
};

export function DashboardSkeleton({
  lines = 3,
  compact = false,
}: DashboardSkeletonProps) {
  return (
    <div
      className={cn("dashboard-skeleton", compact && "dashboard-skeleton--compact")}
      aria-hidden="true"
    >
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className={cn(
            "dashboard-skeleton__line",
            index === 0 && "dashboard-skeleton__line--title",
          )}
        />
      ))}
    </div>
  );
}
