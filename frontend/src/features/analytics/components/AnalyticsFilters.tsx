import { ANALYTICS_PERIODS, type AnalyticsPeriod } from "@/features/analytics/api";
import {
  ANALYTICS_PERIOD_LABELS,
  type AnalyticsFilterState,
} from "@/features/analytics/filter-state";
import { analyticsFiltersSchema } from "@/features/analytics/schemas";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";

type AnalyticsFiltersProps = {
  filters: AnalyticsFilterState;
  onChange: (filters: AnalyticsFilterState) => void;
  onReset: () => void;
};

export function AnalyticsFilters({
  filters,
  onChange,
  onReset,
}: AnalyticsFiltersProps) {
  const validation = analyticsFiltersSchema.safeParse(filters);
  const dateError =
    filters.period === "custom" && !validation.success
      ? validation.error.flatten().fieldErrors.date_to?.[0]
      : undefined;

  function update<K extends keyof AnalyticsFilterState>(
    key: K,
    value: AnalyticsFilterState[K],
  ) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <section className="filters-panel analytics-filters" aria-label="Analytics filters">
      <div className="filters-panel__grid">
        <label className="toolbar__filter" htmlFor="analytics-period">
          <span>Period</span>
          <Select
            id="analytics-period"
            value={filters.period}
            onChange={(event) =>
              update("period", event.target.value as AnalyticsPeriod)
            }
          >
            {ANALYTICS_PERIODS.map((period) => (
              <option key={period} value={period}>
                {ANALYTICS_PERIOD_LABELS[period]}
              </option>
            ))}
          </Select>
        </label>

        <label className="toolbar__filter" htmlFor="analytics-date-from">
          <span>From</span>
          <Input
            id="analytics-date-from"
            type="date"
            value={filters.date_from}
            disabled={filters.period !== "custom"}
            onChange={(event) => update("date_from", event.target.value)}
            aria-invalid={Boolean(dateError)}
          />
        </label>

        <label className="toolbar__filter" htmlFor="analytics-date-to">
          <span>To</span>
          <Input
            id="analytics-date-to"
            type="date"
            value={filters.date_to}
            disabled={filters.period !== "custom"}
            onChange={(event) => update("date_to", event.target.value)}
            aria-invalid={Boolean(dateError)}
            aria-describedby={dateError ? "analytics-date-error" : undefined}
          />
        </label>

        <label className="toolbar__filter" htmlFor="analytics-currency">
          <span>Reporting currency</span>
          <Input
            id="analytics-currency"
            maxLength={3}
            value={filters.reporting_currency}
            onChange={(event) =>
              update("reporting_currency", event.target.value.toUpperCase())
            }
          />
        </label>
      </div>

      {dateError ? (
        <p id="analytics-date-error" className="form-field__error" role="alert">
          {dateError}
        </p>
      ) : null}

      <div className="filters-panel__actions">
        <Button type="button" variant="secondary" size="sm" onClick={onReset}>
          Reset filters
        </Button>
      </div>
    </section>
  );
}
