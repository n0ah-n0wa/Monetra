import type { BudgetCreatePayload, BudgetUpdatePayload } from "@/features/budgets/api";
import type {
  BudgetCreateFormValues,
  BudgetUpdateFormValues,
} from "@/features/budgets/schemas";

export function budgetFormToCreatePayload(
  values: BudgetCreateFormValues,
): BudgetCreatePayload {
  return {
    name: values.name,
    amount: values.amount,
    currency: values.currency,
    period: values.period,
    scope: values.scope,
    start_date: values.start_date,
    end_date: values.period === "custom" ? values.end_date || null : null,
    warning_threshold_percent: values.warning_threshold_percent,
    category_ids: values.scope === "category" ? values.category_ids : [],
  };
}

export function budgetFormToUpdatePayload(
  values: BudgetUpdateFormValues,
): BudgetUpdatePayload {
  const payload: BudgetUpdatePayload = {
    name: values.name,
    amount: values.amount,
    period: values.period,
    scope: values.scope,
    start_date: values.start_date,
    end_date: values.period === "custom" ? values.end_date || null : null,
    warning_threshold_percent: values.warning_threshold_percent,
  };

  if (values.scope === "category") {
    payload.category_ids = values.category_ids;
  }

  return payload;
}
