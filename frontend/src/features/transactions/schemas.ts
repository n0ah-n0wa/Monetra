import { z } from "zod";
import {
  TRANSACTION_SORT_FIELDS,
  TRANSACTION_TYPES,
} from "@/features/transactions/api";
import { compareMoneyStrings, isValidMoneyString } from "@/lib/money";

const moneyField = z
  .string()
  .trim()
  .min(1, "Amount is required.")
  .refine(isValidMoneyString, "Enter a valid amount with up to 4 decimal places.");

const optionalMoneyField = z
  .string()
  .trim()
  .optional()
  .refine((value) => !value || isValidMoneyString(value), {
    message: "Enter a valid amount with up to 4 decimal places.",
  });

export const transactionFormSchema = z.object({
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
  transaction_date: z
    .string()
    .min(1, "Transaction date is required.")
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Enter a valid date."),
  notes: z
    .string()
    .trim()
    .max(2000, "Notes are too long.")
    .optional()
    .or(z.literal("")),
});

export const transactionFiltersSchema = z
  .object({
    account_id: z.string().optional(),
    category_id: z.string().optional(),
    transaction_type: z.enum(TRANSACTION_TYPES).optional().or(z.literal("")),
    date_from: z.string().optional(),
    date_to: z.string().optional(),
    amount_min: optionalMoneyField,
    amount_max: optionalMoneyField,
    currency: z.string().trim().max(3).optional().or(z.literal("")),
    description: z.string().trim().max(500).optional().or(z.literal("")),
    sort_by: z.enum(TRANSACTION_SORT_FIELDS),
    sort_order: z.enum(["asc", "desc"]),
    page_size: z.coerce.number().int().min(1).max(100),
  })
  .refine(
    (values) => {
      if (!values.date_from || !values.date_to) {
        return true;
      }
      return values.date_from <= values.date_to;
    },
    {
      message: "Start date must be on or before end date.",
      path: ["date_to"],
    },
  )
  .refine(
    (values) => {
      if (!values.amount_min || !values.amount_max) {
        return true;
      }
      return compareMoneyStrings(values.amount_min, values.amount_max) <= 0;
    },
    {
      message: "Minimum amount must be less than or equal to maximum amount.",
      path: ["amount_max"],
    },
  );

export type TransactionFormValues = z.infer<typeof transactionFormSchema>;
export type TransactionFiltersValues = z.infer<typeof transactionFiltersSchema>;

export function todayIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
