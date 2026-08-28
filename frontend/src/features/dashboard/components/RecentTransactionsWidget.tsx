import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/Badge";
import { DashboardWidget } from "@/features/dashboard/components/DashboardWidget";
import { useTransactionsQuery } from "@/features/transactions/hooks";
import { formatMoneyDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";
import { formatTransactionType } from "@/features/transactions/api";

export function RecentTransactionsWidget() {
  const query = useTransactionsQuery({
    page: 1,
    page_size: 5,
    sort_by: "transaction_date",
    sort_order: "desc",
  });

  return (
    <DashboardWidget
      title="Recent transactions"
      description="Latest activity across your accounts."
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={query.isSuccess && query.data.items.length === 0}
      emptyTitle="No transactions yet"
      emptyDescription="Record income or expenses to see recent activity here."
      emptyActionLabel="Add transaction"
      emptyActionHref={routes.transactionNew}
      skeletonLines={5}
    >
      <div className="dashboard-list" role="list" aria-label="Recent transactions">
        {query.data?.items.map((transaction) => (
          <article
            key={transaction.id}
            className="dashboard-list__item"
            role="listitem"
          >
            <div className="dashboard-list__main">
              <Link
                className="dashboard-list__title"
                to={routes.transactionDetail(transaction.id)}
              >
                {transaction.description}
              </Link>
              <p className="dashboard-list__meta">
                {transaction.transaction_date} ·{" "}
                {formatTransactionType(transaction.transaction_type)}
              </p>
            </div>
            <div className="dashboard-list__aside">
              <Badge
                variant={
                  transaction.transaction_type === "income" ? "success" : "neutral"
                }
              >
                {formatTransactionType(transaction.transaction_type)}
              </Badge>
              <span className="dashboard-list__amount">
                {formatMoneyDisplay(transaction.amount, transaction.currency)}
              </span>
            </div>
          </article>
        ))}
      </div>
      <p className="dashboard-widget__footer">
        <Link to={routes.transactions}>View all transactions</Link>
      </p>
    </DashboardWidget>
  );
}
