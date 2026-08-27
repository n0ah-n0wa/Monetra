import { z } from "zod";
import { isValidMoneyString } from "@/lib/money";

const moneyField = z
  .string()
  .trim()
  .min(1, "Amount is required.")
  .refine(isValidMoneyString, "Enter a valid amount with up to 4 decimal places.");

const optionalMoneyField = z
  .string()
  .trim()
  .refine((value) => !value || isValidMoneyString(value), {
    message: "Enter a valid amount with up to 4 decimal places.",
  });

export const goalCreateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Goal name is required.")
    .max(120, "Goal name must be 120 characters or fewer."),
  target_amount: moneyField,
  current_amount: optionalMoneyField,
  currency: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^[A-Z]{3}$/, "Enter a 3-letter currency code."),
  target_date: z.string().optional().or(z.literal("")),
  linked_account_id: z.string().optional().or(z.literal("")),
});

export const goalUpdateSchema = goalCreateSchema;

export type GoalCreateFormValues = z.infer<typeof goalCreateSchema>;
export type GoalUpdateFormValues = z.infer<typeof goalUpdateSchema>;
