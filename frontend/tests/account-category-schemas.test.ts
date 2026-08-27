import { describe, expect, it } from "vitest";
import { accountCreateSchema, accountUpdateSchema } from "@/features/accounts/schemas";
import {
  categoryCreateSchema,
  categoryUpdateSchema,
} from "@/features/categories/schemas";

describe("account schemas", () => {
  it("accepts a valid create payload", () => {
    const result = accountCreateSchema.safeParse({
      name: "Checking",
      account_type: "bank",
      currency: "usd",
      opening_balance: "12.50",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.currency).toBe("USD");
    }
  });

  it("rejects invalid currency and balance", () => {
    const result = accountCreateSchema.safeParse({
      name: "Checking",
      account_type: "bank",
      currency: "US",
      opening_balance: "abc",
    });
    expect(result.success).toBe(false);
  });

  it("requires name on update", () => {
    const result = accountUpdateSchema.safeParse({
      name: "",
      account_type: "cash",
    });
    expect(result.success).toBe(false);
  });
});

describe("category schemas", () => {
  it("accepts income and expense types", () => {
    expect(
      categoryCreateSchema.safeParse({
        name: "Salary",
        category_type: "income",
        icon: "",
        color: "",
      }).success,
    ).toBe(true);
  });

  it("rejects empty category names", () => {
    expect(
      categoryUpdateSchema.safeParse({
        name: "   ",
        icon: "",
        color: "",
      }).success,
    ).toBe(false);
  });
});
