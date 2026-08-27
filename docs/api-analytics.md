# Analytics API

Dedicated server-side analytics endpoints for dashboard and reporting.

Base path: `/api/v1/analytics`

All endpoints require authentication. Monetary values use exact decimal arithmetic and are returned in the user's reporting currency unless `reporting_currency` is overridden.

## Period presets

| Query param | Description |
|-------------|-------------|
| `period=last_7_days` | Inclusive 7-day window ending on `as_of_date` |
| `period=last_30_days` | Inclusive 30-day window |
| `period=last_90_days` | Inclusive 90-day window |
| `period=current_month` | First day of month through `as_of_date` |
| `period=previous_month` | Full previous calendar month |
| `period=current_year` | January 1 through `as_of_date` |
| `period=previous_year` | Full previous calendar year |
| `period=custom` | Requires `date_from` and `date_to` |

`as_of_date` defaults to the current UTC calendar date when omitted.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/income-vs-expenses` | Total income and expenses (transfers excluded) |
| GET | `/net-cash-flow` | Income, expenses, and net cash flow time series |
| GET | `/balance-over-time` | Daily total balance including transfers |
| GET | `/spending-by-category` | Expense totals grouped by category |
| GET | `/spending-trends` | Expense trend buckets (day/week/month) |
| GET | `/savings-rate` | Net cash flow and savings rate percentage |
| GET | `/period-comparison` | Current vs immediately preceding equal-length period |
| GET | `/largest-expenses` | Top expenses by amount (`limit`, default 10) |
| GET | `/largest-income` | Top income transactions by amount |
| GET | `/budget-utilization` | Budget utilization snapshot for active budgets |

## Rules

- **Transfers** are excluded from income, expense, category, and savings metrics.
- **Balance over time** includes transfers and opening balances across all accounts (including archived).
- **Multi-currency** amounts convert to the reporting currency using stored exchange rates on each transaction date.
- Missing rates return `422` with code `MISSING_EXCHANGE_RATE` (no silent zero conversion).
- **Empty periods** return zero totals and empty series where applicable.
- **Period comparison** for `current_month` / `current_year` uses the prior calendar month/year; rolling/custom presets use an equal-length preceding window.
- **Largest income/expenses** are ranked by reporting-currency amount after conversion.

## Example

```http
GET /api/v1/analytics/income-vs-expenses?period=current_month&as_of_date=2026-01-15
Authorization: Bearer <token>
```

```json
{
  "period": {
    "preset": "current_month",
    "start_date": "2026-01-01",
    "end_date": "2026-01-15",
    "as_of_date": "2026-01-15"
  },
  "reporting_currency": "USD",
  "income": "5000.0000",
  "expenses": "2200.0000"
}
```
