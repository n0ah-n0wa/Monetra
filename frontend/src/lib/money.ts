/**
 * Money helpers that avoid floating-point arithmetic.
 * Amounts are handled as decimal strings end-to-end.
 */

const MONEY_PATTERN = /^-?\d+(\.\d{1,4})?$/;

export function isValidMoneyString(value: string): boolean {
  return MONEY_PATTERN.test(value.trim());
}

export function normalizeMoneyInput(value: string): string {
  return value.trim();
}

export function formatMoneyDisplay(amount: string, currency: string): string {
  const normalized = amount.trim();
  if (!MONEY_PATTERN.test(normalized)) {
    return `${normalized} ${currency}`;
  }

  const negative = normalized.startsWith("-");
  const unsigned = negative ? normalized.slice(1) : normalized;
  const [integerPart, fractionPart = ""] = unsigned.split(".");
  const groupedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const fraction = `${fractionPart}00`.slice(0, 2);
  const prefix = currency === "USD" ? "$" : `${currency} `;

  return `${negative ? "-" : ""}${prefix}${groupedInteger}.${fraction}`;
}

export function compareMoneyStrings(left: string, right: string): number {
  const normalize = (value: string) => {
    const trimmed = value.trim();
    const negative = trimmed.startsWith("-");
    const unsigned = negative ? trimmed.slice(1) : trimmed;
    const [whole, fraction = ""] = unsigned.split(".");
    const paddedFraction = `${fraction}0000`.slice(0, 4);
    return {
      negative,
      whole: whole.replace(/^0+(?=\d)/, "") || "0",
      fraction: paddedFraction,
    };
  };

  const a = normalize(left);
  const b = normalize(right);

  if (a.negative !== b.negative) {
    return a.negative ? -1 : 1;
  }

  const wholeCompare = a.whole.length - b.whole.length;
  if (wholeCompare !== 0) {
    return a.negative ? -wholeCompare : wholeCompare;
  }
  if (a.whole !== b.whole) {
    return a.negative
      ? a.whole.localeCompare(b.whole) * -1
      : a.whole.localeCompare(b.whole);
  }

  const fractionCompare = a.fraction.localeCompare(b.fraction);
  return a.negative ? fractionCompare * -1 : fractionCompare;
}

/** Formats a backend decimal percent string (e.g. "75.0000") for display. */
export function formatPercentDisplay(value: string | null | undefined): string {
  if (value === null || value === undefined || value.trim() === "") {
    return "—";
  }

  const trimmed = value.trim();
  if (!trimmed.includes(".")) {
    return `${trimmed}%`;
  }

  const [whole, fraction = ""] = trimmed.split(".");
  const trimmedFraction = fraction.replace(/0+$/, "");
  if (!trimmedFraction) {
    return `${whole}%`;
  }
  return `${whole}.${trimmedFraction}%`;
}

/**
 * Clamps a backend percent string to 0–100 for progress-bar width.
 * Display-only; does not affect financial calculations.
 */
export function percentToBarWidth(percent: string | null | undefined): string {
  if (percent === null || percent === undefined || percent.trim() === "") {
    return "0%";
  }

  const trimmed = percent.trim();
  const numeric = Number(trimmed);
  if (Number.isNaN(numeric)) {
    return "0%";
  }

  const clamped = Math.min(100, Math.max(0, numeric));
  return `${clamped}%`;
}
