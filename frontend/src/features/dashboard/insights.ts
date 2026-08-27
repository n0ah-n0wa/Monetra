import type {
  BudgetUtilizationAnalyticsResponse,
  LargestTransactionsResponse,
  PeriodComparisonResponse,
  SavingsRateResponse,
  SpendingByCategoryResponse,
} from "@/features/analytics/api";
import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";

export type FinancialInsight = {
  id: string;
  title: string;
  detail: string;
};

function trendLabel(changePercent: string | null, metric: string): string | null {
  if (changePercent === null || changePercent.trim() === "") {
    return null;
  }
  const trimmed = changePercent.trim();
  if (trimmed.startsWith("-")) {
    return `${metric} decreased by ${formatPercentDisplay(trimmed.slice(1))} vs last month`;
  }
  if (trimmed === "0" || trimmed === "0.0000" || trimmed.startsWith("0.0000")) {
    return `${metric} is unchanged vs last month`;
  }
  return `${metric} increased by ${formatPercentDisplay(trimmed)} vs last month`;
}

export function buildFinancialInsights(input: {
  spendingByCategory?: SpendingByCategoryResponse;
  largestExpenses?: LargestTransactionsResponse;
  periodComparison?: PeriodComparisonResponse;
  savingsRate?: SavingsRateResponse;
  budgetUtilization?: BudgetUtilizationAnalyticsResponse;
}): FinancialInsight[] {
  const insights: FinancialInsight[] = [];

  const topCategory = input.spendingByCategory?.items[0];
  if (topCategory) {
    insights.push({
      id: "top-category",
      title: "Largest expense category",
      detail: `${topCategory.category_name}: ${formatMoneyDisplay(
        topCategory.amount,
        input.spendingByCategory?.reporting_currency ?? "USD",
      )} (${formatPercentDisplay(topCategory.percentage)} of expenses)`,
    });
  }

  const largestExpense = input.largestExpenses?.items[0];
  if (largestExpense) {
    insights.push({
      id: "largest-expense",
      title: "Largest transaction",
      detail: `${largestExpense.description} on ${largestExpense.transaction_date} — ${formatMoneyDisplay(
        largestExpense.reporting_amount,
        input.largestExpenses?.reporting_currency ?? "USD",
      )}`,
    });
  }

  const expenseTrend = input.periodComparison
    ? trendLabel(input.periodComparison.expenses.change_percent, "Spending")
    : null;
  if (expenseTrend) {
    insights.push({
      id: "expense-trend",
      title: "Month-over-month spending",
      detail: expenseTrend,
    });
  }

  const incomeTrend = input.periodComparison
    ? trendLabel(input.periodComparison.income.change_percent, "Income")
    : null;
  if (incomeTrend) {
    insights.push({
      id: "income-trend",
      title: "Month-over-month income",
      detail: incomeTrend,
    });
  }

  if (input.savingsRate?.savings_rate_percent) {
    insights.push({
      id: "savings-rate",
      title: "Savings rate",
      detail: `You saved ${formatPercentDisplay(input.savingsRate.savings_rate_percent)} of income this month (${formatMoneyDisplay(
        input.savingsRate.net_cash_flow,
        input.savingsRate.reporting_currency,
      )} net cash flow).`,
    });
  }

  const warningBudgets =
    input.budgetUtilization?.items.filter(
      (item) =>
        item.utilization.status === "warning" || item.utilization.status === "exceeded",
    ) ?? [];
  for (const item of warningBudgets.slice(0, 2)) {
    insights.push({
      id: `budget-${item.budget.id}`,
      title:
        item.utilization.status === "exceeded"
          ? "Budget exceeded"
          : "Budget nearing limit",
      detail: `${item.budget.name} is at ${formatPercentDisplay(item.utilization.percentage_used)} (${formatMoneyDisplay(
        item.utilization.spent_amount,
        item.budget.currency,
      )} of ${formatMoneyDisplay(item.utilization.budget_amount, item.budget.currency)}).`,
    });
  }

  return insights;
}
