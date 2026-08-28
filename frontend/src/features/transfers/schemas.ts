import { z } from "zod";

export const transferSchema = z
  .object({
    source_account_id: z.string().uuid("Select a source account."),
    destination_account_id: z.string().uuid("Select a destination account."),
    source_amount: z
      .string()
      .trim()
      .min(1, "Enter an amount.")
      .refine((value) => /^\d+(\.\d{1,4})?$/.test(value), {
        message: "Enter a valid amount with up to four decimal places.",
      }),
    transaction_date: z.string().min(1, "Select a date."),
    description: z.string().trim().max(500).optional().or(z.literal("")),
  })
  .refine((values) => values.source_account_id !== values.destination_account_id, {
    message: "Source and destination accounts must be different.",
    path: ["destination_account_id"],
  });

export type TransferFormValues = z.infer<typeof transferSchema>;
