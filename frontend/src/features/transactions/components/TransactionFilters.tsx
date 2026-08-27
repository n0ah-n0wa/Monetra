import type { Account } from "@/features/accounts/api";
import type { Category } from "@/features/categories/api";
import {
  TRANSACTION_SORT_FIELDS,
  TRANSACTION_TYPES,
  formatSortField,
  formatTransactionType,
  type SortOrder,
  type TransactionListParams,
  type TransactionSortField,
  type TransactionType,
} from "@/features/transactions/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
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

type TransactionFiltersProps = {
  filters: TransactionFilterState;
  accounts: Account[];
  categories: Category[];
  onChange: (filters: TransactionFilterState) => void;
  onReset: () => void;
};

export function TransactionFilters({
  filters,
  accounts,
  categories,
  onChange,
  onReset,
}: TransactionFiltersProps) {
  function update<K extends keyof TransactionFilterState>(
    key: K,
    value: TransactionFilterState[K],
  ) {
    onChange({
      ...filters,
      [key]: value,
      page: key === "page" ? (value as number) : 1,
    });
  }

  return (
    <section className="filters-panel" aria-label="Transaction filters">
      <div className="filters-panel__grid">
        <label className="toolbar__filter" htmlFor="transaction-search">
          <span>Search</span>
          <Input
            id="transaction-search"
            type="search"
            placeholder="Description contains…"
            value={filters.description}
            onChange={(event) => update("description", event.target.value)}
          />
        </label>

        <label className="toolbar__filter" htmlFor="transaction-account-filter">
          <span>Account</span>
          <Select
            id="transaction-account-filter"
            value={filters.account_id}
            onChange={(event) => update("account_id", event.target.value)}
          >
            <option value="">All accounts</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </Select>
        </label>

        <label className="toolbar__filter" htmlFor="transaction-category-filter">
          <span>Category</span>
          <Select
            id="transaction-category-filter"
            value={filters.category_id}
            onChange={(event) => update("category_id", event.target.value)}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </Select>
        </label>

        <label className="toolbar__filter" htmlFor="transaction-type-filter">
          <span>Type</span>
          <Select
            id="transaction-type-filter"
            value={filters.transaction_type}
            onChange={(event) =>
              update("transaction_type", event.target.value as TransactionType | "")
            }
          >
            <option value="">All types</option>
            {TRANSACTION_TYPES.map((type) => (
              <option key={type} value={type}>
                {formatTransactionType(type)}
              </option>
            ))}
          </Select>
        </label>

        <label className="toolbar__filter" htmlFor="transaction-date-from">
          <span>From</span>
          <Input
            id="transaction-date-from"
            type="date"
            value={filters.date_from}
            onChange={(event) => update("date_from", event.target.value)}
          />
        </label>

        <label className="toolbar__filter" htmlFor="transaction-date-to">
          <span>To</span>
          <Input
            id="transaction-date-to"
            type="date"
            value={filters.date_to}
            onChange={(event) => update("date_to", event.target.value)}
          />
        </label>

        <label className="toolbar__filter" htmlFor="transaction-amount-min">
          <span>Min amount</span>
          <Input
            id="transaction-amount-min"
            inputMode="decimal"
            value={filters.amount_min}
            onChange={(event) => update("amount_min", event.target.value)}
          />
        </label>

        <label className="toolbar__filter" htmlFor="transaction-amount-max">
          <span>Max amount</span>
          <Input
            id="transaction-amount-max"
            inputMode="decimal"
            value={filters.amount_max}
            onChange={(event) => update("amount_max", event.target.value)}
          />
        </label>

        <label className="toolbar__filter" htmlFor="transaction-currency-filter">
          <span>Currency</span>
          <Input
            id="transaction-currency-filter"
            maxLength={3}
            value={filters.currency}
            onChange={(event) => update("currency", event.target.value.toUpperCase())}
          />
        </label>

        <label className="toolbar__filter" htmlFor="transaction-sort-by">
          <span>Sort by</span>
          <Select
            id="transaction-sort-by"
            value={filters.sort_by}
            onChange={(event) =>
              update("sort_by", event.target.value as TransactionSortField)
            }
          >
            {TRANSACTION_SORT_FIELDS.map((field) => (
              <option key={field} value={field}>
                {formatSortField(field)}
              </option>
            ))}
          </Select>
        </label>

        <label className="toolbar__filter" htmlFor="transaction-sort-order">
          <span>Order</span>
          <Select
            id="transaction-sort-order"
            value={filters.sort_order}
            onChange={(event) => update("sort_order", event.target.value as SortOrder)}
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </Select>
        </label>

        <label className="toolbar__filter" htmlFor="transaction-page-size">
          <span>Page size</span>
          <Select
            id="transaction-page-size"
            value={String(filters.page_size)}
            onChange={(event) => update("page_size", Number(event.target.value))}
          >
            {[10, 20, 50, 100].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </Select>
        </label>
      </div>

      <div className="filters-panel__actions">
        <Button type="button" variant="secondary" size="sm" onClick={onReset}>
          Reset filters
        </Button>
      </div>
    </section>
  );
}

type PaginationProps = {
  page: number;
  totalPages: number;
  totalItems: number;
  onPageChange: (page: number) => void;
};

export function TransactionPagination({
  page,
  totalPages,
  totalItems,
  onPageChange,
}: PaginationProps) {
  if (totalItems === 0) {
    return null;
  }

  return (
    <nav className="pagination" aria-label="Transaction pages">
      <p className="pagination__summary" aria-live="polite">
        Page {page} of {Math.max(totalPages, 1)} · {totalItems} transaction
        {totalItems === 1 ? "" : "s"}
      </p>
      <div className="pagination__actions">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={totalPages === 0 || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </Button>
      </div>
    </nav>
  );
}
