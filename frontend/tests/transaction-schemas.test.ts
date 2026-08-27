import { describe, expect, it } from "vitest";
import {
  transactionFiltersSchema,
  transactionFormSchema,
} from "@/features/transactions/schemas";

describe("transactionFormSchema", () => {
  it("accepts valid transaction input", () => {
    const result = transactionFormSchema.safeParse({
      account_id: "acc-1",
      category_id: "cat-1",
      transaction_type: "expense",
      amount: "25.5000",
      description: "Coffee",
      transaction_date: "2026-02-01",
      notes: "",
    });
    expect(result.success).toBe(true);
  });

  it("rejects invalid amounts", () => {
    const result = transactionFormSchema.safeParse({
      account_id: "acc-1",
      category_id: "cat-1",
      transaction_type: "expense",
      amount: "not-a-number",
      description: "Coffee",
      transaction_date: "2026-02-01",
      notes: "",
    });
    expect(result.success).toBe(false);
  });
});

describe("transactionFiltersSchema", () => {
  it("rejects inverted date ranges", () => {
    const result = transactionFiltersSchema.safeParse({
      account_id: "",
      category_id: "",
      transaction_type: "",
      date_from: "2026-02-10",
      date_to: "2026-02-01",
      amount_min: "",
      amount_max: "",
      currency: "",
      description: "",
      sort_by: "transaction_date",
      sort_order: "desc",
      page_size: 20,
    });
    expect(result.success).toBe(false);
  });

  it("rejects inverted amount ranges", () => {
    const result = transactionFiltersSchema.safeParse({
      account_id: "",
      category_id: "",
      transaction_type: "",
      date_from: "",
      date_to: "",
      amount_min: "50",
      amount_max: "10",
      currency: "",
      description: "",
      sort_by: "amount",
      sort_order: "asc",
      page_size: 20,
    });
    expect(result.success).toBe(false);
  });

  it("accepts decimal amount ranges compared numerically", () => {
    const result = transactionFiltersSchema.safeParse({
      account_id: "",
      category_id: "",
      transaction_type: "",
      date_from: "",
      date_to: "",
      amount_min: "9",
      amount_max: "10",
      currency: "",
      description: "",
      sort_by: "amount",
      sort_order: "asc",
      page_size: 20,
    });
    expect(result.success).toBe(true);
  });
});
