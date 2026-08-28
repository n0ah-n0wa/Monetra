import { describe, expect, it } from "vitest";
import {
  budgetFormToCreatePayload,
  budgetFormToUpdatePayload,
} from "@/features/budgets/budget-form-payload";
import type {
  BudgetCreateFormValues,
  BudgetUpdateFormValues,
} from "@/features/budgets/schemas";

const baseValues: BudgetCreateFormValues = {
  name: "Groceries",
  amount: "500.0000",
  currency: "USD",
  period: "monthly",
  scope: "overall",
  start_date: "2026-01-01",
  end_date: "",
  warning_threshold_percent: 80,
  category_ids: [],
};

describe("budgetFormToCreatePayload", () => {
  it("sends an empty category list for overall budgets", () => {
    expect(budgetFormToCreatePayload(baseValues).category_ids).toEqual([]);
  });

  it("sends category ids for category-scoped budgets", () => {
    const payload = budgetFormToCreatePayload({
      ...baseValues,
      scope: "category",
      category_ids: ["cat-1"],
    });
    expect(payload.category_ids).toEqual(["cat-1"]);
  });
});

describe("budgetFormToUpdatePayload", () => {
  it("omits category_ids for overall budgets", () => {
    const payload = budgetFormToUpdatePayload(baseValues as BudgetUpdateFormValues);
    expect(payload).not.toHaveProperty("category_ids");
  });

  it("includes category_ids for category-scoped budgets", () => {
    const payload = budgetFormToUpdatePayload({
      ...baseValues,
      scope: "category",
      category_ids: ["cat-1", "cat-2"],
    } as BudgetUpdateFormValues);
    expect(payload.category_ids).toEqual(["cat-1", "cat-2"]);
  });
});
