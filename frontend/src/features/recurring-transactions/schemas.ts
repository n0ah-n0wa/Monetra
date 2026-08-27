import { z } from "zod";
import { RECURRING_FREQUENCIES } from "@/features/recurring-transactions/api";
import { TRANSACTION_TYPES } from "@/features/transactions/api";
import { todayIsoDate } from "@/features/transactions/schemas";
import { isValidMoneyString } from "@/lib/money";

const moneyField = z
  .string()
  .trim()
  .min(1, "Amount is required.")
  .refine(isValidMoneyString, "Enter a valid amount with up to 4 decimal places.");

const baseRecurringSchema = z.object({
  account_id: z.string().min(1, "Select an account."),
  category_id: z.string().min(1, "Select a category."),
  transaction_type: z.enum(TRANSACTION_TYPES, {
    required_error: "Select a transaction type.",
  }),
  amount: moneyField,
  description: z
    .string()
    .trim()
    .min(1, "Description is required.")
    .max(500, "Description must be 500 characters or fewer."),
  frequency: z.enum(RECURRING_FREQUENCIES, {
    required_error: "Select a frequency.",
  }),
  start_date: z
    .string()
    .min(1, "Start date is required.")
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Enter a valid date."),
  end_date: z.string().optional().or(z.literal("")),
});

export const recurringTransactionCreateSchema = baseRecurringSchema.refine(
  (values) => {
    if (!values.end_date) {
      return true;
    }
    return values.start_date <= values.end_date;
  },
  {
    message: "Start date must be on or before end date.",
    path: ["end_date"],
  },
);

export const recurringTransactionUpdateSchema = baseRecurringSchema.refine(
  (values) => {
    if (!values.end_date) {
      return true;
    }
    return values.start_date <= values.end_date;
  },
  {
    message: "Start date must be on or before end date.",
    path: ["end_date"],
  },
);

export type RecurringTransactionCreateFormValues = z.infer<
  typeof recurringTransactionCreateSchema
>;
export type RecurringTransactionUpdateFormValues = z.infer<
  typeof recurringTransactionUpdateSchema
>;

export { todayIsoDate };
