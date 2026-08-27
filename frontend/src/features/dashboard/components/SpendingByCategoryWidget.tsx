import { Link } from "react-router-dom";
import { DashboardWidget } from "@/features/dashboard/components/DashboardWidget";
import { useSpendingByCategoryQuery } from "@/features/analytics/hooks";
import {
  formatMoneyDisplay,
  formatPercentDisplay,
  percentToBarWidth,
} from "@/lib/money";
import { routes } from "@/lib/routes";

export function SpendingByCategoryWidget() {
  const query = useSpendingByCategoryQuery();

  return (
    <DashboardWidget
      title="Spending by category"
      description="Where your money went this month."
      isLoading={query.isPending}
      isError={query.isError}
      error={query.error}
      onRetry={() => void query.refetch()}
      isEmpty={query.isSuccess && query.data.items.length === 0}
      emptyTitle="No spending recorded"
      emptyDescription="Expense transactions will appear here by category."
      skeletonLines={5}
    >
      <div className="dashboard-chart" aria-hidden="true">
        {query.data?.items.map((item) => (
          <div key={item.category_id} className="dashboard-chart__row">
            <span className="dashboard-chart__label">{item.category_name}</span>
            <span className="dashboard-chart__track">
              <span
                className="dashboard-chart__bar"
                style={{ width: percentToBarWidth(item.percentage) }}
              />
            </span>
          </div>
        ))}
      </div>

      <table className="dashboard-table">
        <caption className="sr-only">
          Spending by category for the current month
        </caption>
        <thead>
          <tr>
            <th scope="col">Category</th>
            <th scope="col">Amount</th>
            <th scope="col">Share</th>
          </tr>
        </thead>
        <tbody>
          {query.data?.items.map((item) => (
            <tr key={item.category_id}>
              <td>{item.category_name}</td>
              <td>{formatMoneyDisplay(item.amount, query.data.reporting_currency)}</td>
              <td>{formatPercentDisplay(item.percentage)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">Total expenses</th>
            <td colSpan={2}>
              {query.data
                ? formatMoneyDisplay(
                    query.data.total_expenses,
                    query.data.reporting_currency,
                  )
                : "—"}
            </td>
          </tr>
        </tfoot>
      </table>

      <p className="dashboard-widget__footer">
        <Link to={routes.analytics}>Explore analytics</Link>
      </p>
    </DashboardWidget>
  );
}
