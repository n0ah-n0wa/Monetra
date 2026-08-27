import { describe, expect, it } from "vitest";
import {
  defaultAnalyticsFilters,
  filtersToAnalyticsParams,
} from "@/features/analytics/filter-state";
import { analyticsFiltersSchema } from "@/features/analytics/schemas";

describe("analyticsFiltersSchema", () => {
  it("accepts predefined periods", () => {
    const result = analyticsFiltersSchema.safeParse(defaultAnalyticsFilters("EUR"));
    expect(result.success).toBe(true);
  });

  it("requires dates for custom periods", () => {
    const result = analyticsFiltersSchema.safeParse({
      period: "custom",
      date_from: "",
      date_to: "",
      reporting_currency: "USD",
    });
    expect(result.success).toBe(false);
  });
});

describe("filtersToAnalyticsParams", () => {
  it("maps custom periods to query params", () => {
    expect(
      filtersToAnalyticsParams({
        period: "custom",
        date_from: "2026-01-01",
        date_to: "2026-01-31",
        reporting_currency: "usd",
      }),
    ).toEqual({
      period: "custom",
      date_from: "2026-01-01",
      date_to: "2026-01-31",
      reporting_currency: "USD",
    });
  });
});
