import type {
  TransactionCreatePayload,
  TransactionUpdatePayload,
} from "@/features/transactions/api";
import type { TransactionFormValues } from "@/features/transactions/schemas";

export function transactionFormToCreatePayload(
  values: TransactionFormValues,
): TransactionCreatePayload {
  return {
    account_id: values.account_id,
    category_id: values.category_id,
    transaction_type: values.transaction_type,
    amount: values.amount.trim(),
    description: values.description,
    transaction_date: values.transaction_date,
    notes: values.notes?.trim() ? values.notes.trim() : null,
  };
}

export function transactionFormToUpdatePayload(
  values: TransactionFormValues,
): TransactionUpdatePayload {
  return {
    account_id: values.account_id,
    category_id: values.category_id,
    transaction_type: values.transaction_type,
    amount: values.amount.trim(),
    description: values.description,
    transaction_date: values.transaction_date,
    notes: values.notes?.trim() ? values.notes.trim() : null,
  };
}
