import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { Account } from "@/features/accounts/api";
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
    <div className="transaction-table" role="table" aria-label="Transactions">
      <div className="transaction-table__header" role="row">
        <span role="columnheader">Date</span>
        <span role="columnheader">Description</span>
        <span role="columnheader">Account</span>
        <span role="columnheader">Category</span>
        <span role="columnheader">Type</span>
        <span role="columnheader" className="transaction-table__amount">
          Amount
        </span>
        <span role="columnheader">Actions</span>
      </div>
      {transactions.map((transaction) => {
        const accountName = lookupName(accounts, transaction.account_id);
        const categoryName = lookupName(categories, transaction.category_id);
        const amountLabel = formatMoneyDisplay(
          transaction.amount,
          transaction.currency,
        );

        return (
          <article key={transaction.id} className="transaction-table__row" role="row">
            <span role="cell" aria-label={`Date: ${transaction.transaction_date}`}>
              {transaction.transaction_date}
            </span>
            <span role="cell" aria-label={`Description: ${transaction.description}`}>
              <Link
                className="data-card__title"
                to={routes.transactionDetail(transaction.id)}
              >
                {transaction.description}
              </Link>
            </span>
            <span role="cell" aria-label={`Account: ${accountName}`}>
              {accountName}
            </span>
            <span role="cell" aria-label={`Category: ${categoryName}`}>
              {categoryName}
            </span>
            <span
              role="cell"
              aria-label={`Type: ${formatTransactionType(transaction.transaction_type)}`}
            >
              <Badge
                variant={
                  transaction.transaction_type === "income" ? "success" : "neutral"
                }
              >
                {formatTransactionType(transaction.transaction_type)}
              </Badge>
            </span>
            <span
              role="cell"
              className="transaction-table__amount"
              aria-label={`Amount: ${amountLabel}`}
            >
              {amountLabel}
            </span>
            <span role="cell" className="transaction-table__actions">
              <Link
                className="btn btn--secondary btn--sm"
                to={routes.transactionDetail(transaction.id)}
              >
                Edit
              </Link>
              <Button size="sm" variant="danger" onClick={() => onDelete(transaction)}>
                Delete
              </Button>
            </span>
          </article>
        );
      })}
    </div>
  );
}
