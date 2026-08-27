import { describe, expect, it } from "vitest";
import {
  compareMoneyStrings,
  formatMoneyDisplay,
  formatPercentDisplay,
  isValidMoneyString,
  normalizeMoneyInput,
  percentToBarWidth,
} from "@/lib/money";

describe("money utilities", () => {
  it("validates decimal strings without using floats", () => {
    expect(isValidMoneyString("10.0000")).toBe(true);
    expect(isValidMoneyString("0.5")).toBe(true);
    expect(isValidMoneyString("abc")).toBe(false);
    expect(isValidMoneyString("10.12345")).toBe(false);
  });

  it("formats money for display from exact strings", () => {
    expect(formatMoneyDisplay("250.5000", "USD")).toBe("$250.50");
    expect(formatMoneyDisplay("1000", "USD")).toBe("$1,000.00");
  });

  it("formats percent strings from backend", () => {
    expect(formatPercentDisplay("75.0000")).toBe("75%");
    expect(formatPercentDisplay("83.3333")).toBe("83.3333%");
    expect(formatPercentDisplay(null)).toBe("—");
  });

  it("compares money strings lexicographically by decimal value", () => {
    expect(compareMoneyStrings("10.0000", "50.0000")).toBeLessThan(0);
    expect(compareMoneyStrings("50.0000", "10.0000")).toBeGreaterThan(0);
    expect(compareMoneyStrings("10.0000", "10.0000")).toBe(0);
  });

  it("normalizes input by trimming", () => {
    expect(normalizeMoneyInput(" 25.50 ")).toBe("25.50");
  });

  it("clamps percent strings for progress bar width", () => {
    expect(percentToBarWidth("40.0000")).toBe("40%");
    expect(percentToBarWidth("125.0000")).toBe("100%");
    expect(percentToBarWidth("-5")).toBe("0%");
    expect(percentToBarWidth(null)).toBe("0%");
  });
});
