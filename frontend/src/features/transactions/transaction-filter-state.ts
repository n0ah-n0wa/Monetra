import {
  type SortOrder,
  type TransactionListParams,
  type TransactionSortField,
  type TransactionType,
} from "@/features/transactions/api";
import { isValidMoneyString } from "@/lib/money";

export type TransactionFilterState = {
  account_id: string;
  category_id: string;
  transaction_type: TransactionType | "";
  date_from: string;
  date_to: string;
  amount_min: string;
  amount_max: string;
  currency: string;
  description: string;
  sort_by: TransactionSortField;
  sort_order: SortOrder;
  page: number;
  page_size: number;
};

export const defaultTransactionFilters: TransactionFilterState = {
  account_id: "",
  category_id: "",
  transaction_type: "",
  date_from: "",
  date_to: "",
  amount_min: "",
  amount_max: "",
  currency: "",
  description: "",
  sort_by: "transaction_date",
  sort_order: "desc",
  page: 1,
  page_size: 20,
};

export function filtersToQueryParams(
  filters: TransactionFilterState,
): TransactionListParams {
  const amountMin = filters.amount_min.trim();
  const amountMax = filters.amount_max.trim();

  return {
    page: filters.page,
    page_size: filters.page_size,
    account_id: filters.account_id || undefined,
    category_id: filters.category_id || undefined,
    transaction_type: filters.transaction_type || undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
    amount_min: amountMin && isValidMoneyString(amountMin) ? amountMin : undefined,
    amount_max: amountMax && isValidMoneyString(amountMax) ? amountMax : undefined,
    currency: filters.currency || undefined,
    description: filters.description || undefined,
    sort_by: filters.sort_by,
    sort_order: filters.sort_order,
  };
}
