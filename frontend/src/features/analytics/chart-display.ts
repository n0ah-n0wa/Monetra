import { formatMoneyDisplay, formatPercentDisplay } from "@/lib/money";

/**
 * Maps a server-computed money string to a chart axis value.
 * Used only for visualization scaling — never for balances or totals.
 */
export function chartScaleValue(amount: string): number {
  const trimmed = amount.trim();
  if (!trimmed) {
    return 0;
  }
  return Number(trimmed);
}

export function formatChartMoneyTooltip(
  amount: string,
  currency: string,
  label?: string,
): string {
  const formatted = formatMoneyDisplay(amount, currency);
  return label ? `${label}: ${formatted}` : formatted;
}

export function formatChartPercentTooltip(percent: string, label?: string): string {
  const formatted = formatPercentDisplay(percent);
  return label ? `${label}: ${formatted}` : formatted;
}
