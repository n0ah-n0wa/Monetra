import { z } from "zod";
import { ACCOUNT_TYPES } from "@/features/accounts/api";

export const accountCreateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Account name is required.")
    .max(120, "Account name must be 120 characters or fewer."),
  account_type: z.enum(ACCOUNT_TYPES, {
    required_error: "Select an account type.",
  }),
  currency: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^[A-Z]{3}$/, "Enter a 3-letter currency code."),
  opening_balance: z
    .string()
    .trim()
    .min(1, "Opening balance is required.")
    .regex(/^-?\d+(\.\d{1,4})?$/, "Enter a valid amount."),
});

export const accountUpdateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Account name is required.")
    .max(120, "Account name must be 120 characters or fewer."),
  account_type: z.enum(ACCOUNT_TYPES, {
    required_error: "Select an account type.",
  }),
});

export type AccountCreateFormValues = z.infer<typeof accountCreateSchema>;
export type AccountUpdateFormValues = z.infer<typeof accountUpdateSchema>;
