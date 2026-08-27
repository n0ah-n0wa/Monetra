import { useMemo, useState } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { BalanceOverTimePanel } from "@/features/analytics/components/BalanceOverTimePanel";
import { BudgetUtilizationPanel } from "@/features/analytics/components/BudgetUtilizationPanel";
import { CashFlowTrendPanel } from "@/features/analytics/components/CashFlowTrendPanel";
import { AnalyticsFilters } from "@/features/analytics/components/AnalyticsFilters";
import { IncomeVsExpensesPanel } from "@/features/analytics/components/IncomeVsExpensesPanel";
import { PeriodComparisonPanel } from "@/features/analytics/components/PeriodComparisonPanel";
import { SpendingByCategoryPanel } from "@/features/analytics/components/SpendingByCategoryPanel";
import {
  defaultAnalyticsFilters,
  filtersToAnalyticsParams,
  formatResolvedPeriod,
} from "@/features/analytics/filter-state";
import { analyticsFiltersSchema } from "@/features/analytics/schemas";
import { useAuth } from "@/features/auth/hooks";

export function AnalyticsPage() {
  const { user } = useAuth();
  const [filters, setFilters] = useState(() =>
    defaultAnalyticsFilters(user?.reporting_currency ?? "USD"),
  );

  const validation = analyticsFiltersSchema.safeParse(filters);
  const queriesEnabled = validation.success;

  const params = useMemo(() => filtersToAnalyticsParams(filters), [filters]);

  const periodSummary = validation.success
    ? filters.period === "custom"
      ? formatResolvedPeriod(
          filters.date_from,
          filters.date_to,
          filters.reporting_currency || user?.reporting_currency || "USD",
        )
      : `Preset: ${filters.period.replaceAll("_", " ")} · ${filters.reporting_currency || user?.reporting_currency || "USD"}`
    : null;

  return (
    <PageContainer>
      <PageHeader
        title="Analytics"
        description="Interactive charts backed by server-side financial analytics. Tables below each chart provide accessible summaries."
      />

      <AnalyticsFilters
        filters={filters}
        onChange={setFilters}
        onReset={() =>
          setFilters(defaultAnalyticsFilters(user?.reporting_currency ?? "USD"))
        }
      />

      {!queriesEnabled ? (
        <Alert variant="warning" title="Select a valid period">
          Choose a predefined period or provide a custom start and end date.
        </Alert>
      ) : null}

      {periodSummary ? (
        <p className="analytics-period-summary" aria-live="polite">
          Viewing {periodSummary}
        </p>
      ) : null}

      <div className="analytics-layout">
        <PeriodComparisonPanel params={params} enabled={queriesEnabled} />
        <IncomeVsExpensesPanel params={params} enabled={queriesEnabled} />
        <SpendingByCategoryPanel params={params} enabled={queriesEnabled} />
        <BalanceOverTimePanel params={params} enabled={queriesEnabled} />
        <CashFlowTrendPanel params={params} enabled={queriesEnabled} />
        <BudgetUtilizationPanel params={params} enabled={queriesEnabled} />
      </div>
    </PageContainer>
  );
}
