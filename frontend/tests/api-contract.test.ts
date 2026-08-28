import { describe, expect, it } from "vitest";
import { ACCOUNT_TYPES } from "@/features/accounts/api";
import { ANALYTICS_PERIODS } from "@/features/analytics/api";
import {
  BUDGET_PERIODS,
  BUDGET_SCOPES,
  BUDGET_UTILIZATION_STATUSES,
} from "@/features/budgets/api";
import { CATEGORY_TYPES } from "@/features/categories/api";
import { GOAL_STATUSES } from "@/features/goals/api";
import { IMPORT_JOB_STATUSES } from "@/features/imports/api";
import { NOTIFICATION_TYPES } from "@/features/notifications/api";
import { RECURRING_FREQUENCIES } from "@/features/recurring-transactions/api";
import {
  TRANSACTION_SORT_FIELDS,
  TRANSACTION_TYPES,
} from "@/features/transactions/api";
import { toSearchParams } from "@/types/pagination";

describe("frontend API enum contracts", () => {
  it("matches backend account and transaction enums", () => {
    expect(ACCOUNT_TYPES).toEqual([
      "cash",
      "bank",
      "savings",
      "credit_card",
      "digital_wallet",
    ]);
    expect(TRANSACTION_TYPES).toEqual(["income", "expense"]);
    expect(TRANSACTION_SORT_FIELDS).toEqual([
      "transaction_date",
      "amount",
      "created_at",
      "description",
    ]);
  });

  it("matches backend budget, goal, and recurring enums", () => {
    expect(BUDGET_PERIODS).toEqual(["weekly", "monthly", "yearly", "custom"]);
    expect(BUDGET_SCOPES).toEqual(["overall", "category"]);
    expect(BUDGET_UTILIZATION_STATUSES).toEqual(["healthy", "warning", "exceeded"]);
    expect(GOAL_STATUSES).toEqual(["active", "completed", "archived"]);
    expect(RECURRING_FREQUENCIES).toEqual([
      "daily",
      "weekly",
      "biweekly",
      "monthly",
      "quarterly",
      "yearly",
    ]);
  });

  it("matches backend category, import, and notification enums", () => {
    expect(CATEGORY_TYPES).toEqual(["income", "expense"]);
    expect(IMPORT_JOB_STATUSES).toEqual([
      "pending",
      "preview",
      "processing",
      "completed",
      "failed",
    ]);
    expect(NOTIFICATION_TYPES).toContain("recurring_created");
    expect(NOTIFICATION_TYPES).toContain("import_completed");
  });

  it("matches backend analytics period presets", () => {
    expect(ANALYTICS_PERIODS).toEqual([
      "last_7_days",
      "last_30_days",
      "last_90_days",
      "current_month",
      "previous_month",
      "current_year",
      "previous_year",
      "custom",
    ]);
  });
});

describe("toSearchParams", () => {
  it("serializes booleans as lowercase strings", () => {
    expect(toSearchParams({ unread_only: true })).toBe("?unread_only=true");
    expect(toSearchParams({ unread_only: false })).toBe("?unread_only=false");
    expect(toSearchParams({ include_system: true })).toBe("?include_system=true");
  });

  it("omits undefined and empty string values", () => {
    expect(toSearchParams({ page: 1, status: undefined, description: "" })).toBe(
      "?page=1",
    );
  });
});
