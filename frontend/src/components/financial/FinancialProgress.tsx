import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { formatPercentDisplay, percentToBarWidth } from "@/lib/money";

type FinancialProgressBarProps = {
  percentage: string;
  label: string;
  variant?: "budget" | "goal";
  status?: "healthy" | "warning" | "exceeded";
};

export function FinancialProgressBar({
  percentage,
  label,
  variant = "budget",
  status,
}: FinancialProgressBarProps) {
  return (
    <div
      className="dashboard-budget__bar"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuetext={formatPercentDisplay(percentage)}
      aria-label={label}
    >
      <span
        className={cn(
          "dashboard-budget__bar-fill",
          variant === "goal" && "dashboard-budget__bar-fill--goal",
          status === "exceeded" && "dashboard-budget__bar-fill--exceeded",
          status === "warning" && "dashboard-budget__bar-fill--warning",
        )}
        style={{ width: percentToBarWidth(percentage) }}
      />
    </div>
  );
}

type FinancialProgressStat = {
  label: string;
  value: ReactNode;
};

type FinancialProgressStatsProps = {
  stats: FinancialProgressStat[];
};

export function FinancialProgressStats({ stats }: FinancialProgressStatsProps) {
  return (
    <dl className="dashboard-budget__stats">
      {stats.map((stat) => (
        <div key={stat.label}>
          <dt>{stat.label}</dt>
          <dd>{stat.value}</dd>
        </div>
      ))}
    </dl>
  );
}
