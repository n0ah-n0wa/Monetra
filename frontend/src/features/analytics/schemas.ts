import { z } from "zod";
import { ANALYTICS_PERIODS } from "@/features/analytics/api";

export const analyticsFiltersSchema = z
  .object({
    period: z.enum(ANALYTICS_PERIODS),
    date_from: z.string().optional().or(z.literal("")),
    date_to: z.string().optional().or(z.literal("")),
    reporting_currency: z
      .string()
      .trim()
      .length(3, "Enter a 3-letter currency code.")
      .optional()
      .or(z.literal("")),
  })
  .refine(
    (values) => {
      if (values.period !== "custom") {
        return true;
      }
      return Boolean(values.date_from && values.date_to);
    },
    {
      message: "Custom periods require start and end dates.",
      path: ["date_to"],
    },
  )
  .refine(
    (values) => {
      if (values.period !== "custom" || !values.date_from || !values.date_to) {
        return true;
      }
      return values.date_from <= values.date_to;
    },
    {
      message: "Start date must be on or before end date.",
      path: ["date_to"],
    },
  );

export type AnalyticsFiltersValues = z.infer<typeof analyticsFiltersSchema>;
