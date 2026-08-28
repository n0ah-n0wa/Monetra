import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { Account } from "@/features/accounts/api";
import { AccessibleDataTable } from "@/features/analytics/components/AccessibleDataTable";
import type { Category } from "@/features/categories/api";
import { formatTransactionType, type Transaction } from "@/features/transactions/api";
import { routes } from "@/lib/routes";
import { formatMoneyDisplay } from "@/lib/money";

type TransactionListProps = {
  transactions: Transaction[];
  accounts: Account[];
  categories: Category[];
  onDelete: (transaction: Transaction) => void;
};

function lookupName<T extends { id: string; name: string }>(
  items: T[],
  id: string,
): string {
  return items.find((item) => item.id === id)?.name ?? id;
}

export function TransactionList({
  transactions,
  accounts,
  categories,
  onDelete,
}: TransactionListProps) {
  return (
    <AccessibleDataTable
      caption="Transactions"
      className="transaction-data-table"
      rows={transactions}
      getRowKey={(transaction) => transaction.id}
      columns={[
        {
          key: "date",
          header: "Date",
          cell: (transaction) => transaction.transaction_date,
        },
        {
          key: "description",
          header: "Description",
          cell: (transaction) => (
            <Link
              className="data-card__title"
              to={routes.transactionDetail(transaction.id)}
            >
              {transaction.description}
            </Link>
          ),
        },
        {
          key: "account",
          header: "Account",
          cell: (transaction) => lookupName(accounts, transaction.account_id),
        },
        {
          key: "category",
          header: "Category",
          cell: (transaction) => lookupName(categories, transaction.category_id),
        },
        {
          key: "type",
          header: "Type",
          cell: (transaction) => (
            <Badge
              variant={
                transaction.transaction_type === "income" ? "success" : "neutral"
              }
            >
              {formatTransactionType(transaction.transaction_type)}
            </Badge>
          ),
        },
        {
          key: "amount",
          header: "Amount",
          align: "right",
          cellClassName: "transaction-data-table__amount",
          cell: (transaction) =>
            formatMoneyDisplay(transaction.amount, transaction.currency),
        },
        {
          key: "actions",
          header: "Actions",
          cellClassName: "transaction-data-table__actions",
          cell: (transaction) => (
            <>
              <Link
                className="btn btn--secondary btn--sm"
                to={routes.transactionDetail(transaction.id)}
                aria-label={`View ${transaction.description}`}
              >
                View
              </Link>
              <Button
                size="sm"
                variant="danger"
                onClick={() => onDelete(transaction)}
                aria-label={`Delete ${transaction.description}`}
              >
                Delete
              </Button>
            </>
          ),
        },
      ]}
    />
  );
}
