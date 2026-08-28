import { z } from "zod";
import { BUDGET_PERIODS, BUDGET_SCOPES } from "@/features/budgets/api";
import { isValidMoneyString } from "@/lib/money";

const moneyField = z
  .string()
  .trim()
  .min(1, "Amount is required.")
  .refine(isValidMoneyString, "Enter a valid amount with up to 4 decimal places.");

const baseBudgetSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Budget name is required.")
    .max(120, "Budget name must be 120 characters or fewer."),
  amount: moneyField,
  currency: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^[A-Z]{3}$/, "Enter a 3-letter currency code."),
  period: z.enum(BUDGET_PERIODS, { required_error: "Select a period." }),
  scope: z.enum(BUDGET_SCOPES, { required_error: "Select a scope." }),
  start_date: z
    .string()
    .min(1, "Start date is required.")
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Enter a valid date."),
  end_date: z.string().optional().or(z.literal("")),
  warning_threshold_percent: z.coerce
    .number()
    .int()
    .min(0, "Threshold must be at least 0.")
    .max(100, "Threshold cannot exceed 100."),
  category_ids: z.array(z.string()),
});

export const budgetCreateSchema = baseBudgetSchema
  .refine((values) => values.period !== "custom" || Boolean(values.end_date), {
    message: "Custom budgets require an end date.",
    path: ["end_date"],
  })
  .refine((values) => values.scope !== "category" || values.category_ids.length > 0, {
    message: "Select at least one category.",
    path: ["category_ids"],
  })
  .refine(
    (values) => {
      if (!values.end_date || !values.start_date) {
        return true;
      }
      return values.start_date <= values.end_date;
    },
    {
      message: "Start date must be on or before end date.",
      path: ["end_date"],
    },
  );

export const budgetUpdateSchema = baseBudgetSchema
  .omit({ currency: true })
  .refine((values) => values.period !== "custom" || Boolean(values.end_date), {
    message: "Custom budgets require an end date.",
    path: ["end_date"],
  })
  .refine((values) => values.scope !== "category" || values.category_ids.length > 0, {
    message: "Select at least one category.",
    path: ["category_ids"],
  })
  .refine(
    (values) => {
      if (!values.end_date || !values.start_date) {
        return true;
      }
      return values.start_date <= values.end_date;
    },
    {
      message: "Start date must be on or before end date.",
      path: ["end_date"],
    },
  );

export type BudgetCreateFormValues = z.infer<typeof budgetCreateSchema>;
export type BudgetUpdateFormValues = z.infer<typeof budgetUpdateSchema>;
