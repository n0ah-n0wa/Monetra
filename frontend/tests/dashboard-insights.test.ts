import { describe, expect, it } from "vitest";
import { buildFinancialInsights } from "@/features/dashboard/insights";

describe("buildFinancialInsights", () => {
  it("builds insights from backend analytics payloads without client-side math", () => {
    const insights = buildFinancialInsights({
      spendingByCategory: {
        period: {
          preset: "current_month",
          start_date: "2026-02-01",
          end_date: "2026-02-28",
          as_of_date: "2026-02-15",
        },
        reporting_currency: "USD",
        total_expenses: "500.0000",
        items: [
          {
            category_id: "cat-1",
            category_name: "Groceries",
            amount: "300.0000",
            percentage: "60.0000",
          },
        ],
      },
      largestExpenses: {
        period: {
          preset: "current_month",
          start_date: "2026-02-01",
          end_date: "2026-02-28",
          as_of_date: "2026-02-15",
        },
        reporting_currency: "USD",
        items: [
          {
            transaction_id: "txn-1",
            description: "Rent",
            amount: "1200.0000",
            currency: "USD",
            reporting_amount: "1200.0000",
            transaction_date: "2026-02-01",
            category_name: "Housing",
            account_name: "Checking",
          },
        ],
      },
      periodComparison: {
        current_period: {
          preset: "current_month",
          start_date: "2026-02-01",
          end_date: "2026-02-28",
          as_of_date: "2026-02-15",
        },
        previous_period: {
          preset: "previous_month",
          start_date: "2026-01-01",
          end_date: "2026-01-31",
          as_of_date: "2026-01-31",
        },
        reporting_currency: "USD",
        income: {
          current: "3000.0000",
          previous: "2800.0000",
          change: "200.0000",
          change_percent: "7.1429",
        },
        expenses: {
          current: "500.0000",
          previous: "600.0000",
          change: "-100.0000",
          change_percent: "-16.6667",
        },
        net_cash_flow: {
          current: "2500.0000",
          previous: "2200.0000",
          change: "300.0000",
          change_percent: "13.6364",
        },
        savings_rate_percent: {
          current: "83.3333",
          previous: "78.5714",
          change: "4.7619",
          change_percent: "6.0606",
        },
      },
      savingsRate: {
        period: {
          preset: "current_month",
          start_date: "2026-02-01",
          end_date: "2026-02-28",
          as_of_date: "2026-02-15",
        },
        reporting_currency: "USD",
        income: "3000.0000",
        expenses: "500.0000",
        net_cash_flow: "2500.0000",
        savings_rate_percent: "83.3333",
      },
      budgetUtilization: {
        period: {
          preset: "current_month",
          start_date: "2026-02-01",
          end_date: "2026-02-28",
          as_of_date: "2026-02-15",
        },
        as_of_date: "2026-02-15",
        items: [
          {
            budget: {
              id: "bud-1",
              name: "Food",
              amount: "400.0000",
              currency: "USD",
              period: "monthly",
              scope: "overall",
              start_date: "2026-02-01",
              end_date: null,
              warning_threshold_percent: 80,
              categories: [],
              archived_at: null,
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-01T00:00:00Z",
              utilization: null,
            },
            utilization: {
              as_of_date: "2026-02-15",
              period_start: "2026-02-01",
              period_end: "2026-02-28",
              budget_amount: "400.0000",
              spent_amount: "350.0000",
              remaining_amount: "50.0000",
              percentage_used: "87.5000",
              status: "warning",
            },
          },
        ],
      },
    });

    expect(insights.some((item) => item.id === "top-category")).toBe(true);
    expect(insights.some((item) => item.id === "largest-expense")).toBe(true);
    expect(insights.some((item) => item.id === "budget-bud-1")).toBe(true);
    expect(insights.some((item) => item.title === "Savings rate")).toBe(true);
  });
});
