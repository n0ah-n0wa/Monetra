# Budgets API

Base path: `/api/v1/budgets`

Budgets track expense spending against a configured limit. Transfers are excluded from all budget calculations; only expense transactions count toward `spent_amount`.

## Scopes

- `category` — one or more linked expense/universal categories
- `overall` — all expense transactions in the budget currency

## Periods

| Period | Window |
|--------|--------|
| `weekly` | 7-day windows anchored to `start_date` |
| `monthly` | Calendar-month-style windows anchored to `start_date` day (clamped to month-end) |
| `yearly` | 12-month windows anchored to `start_date` |
| `custom` | Single window from `start_date` through `end_date` (requires `end_date`) |

## Utilization

Each budget exposes:

- `budget_amount` — configured limit
- `spent_amount` — summed expenses in the active period
- `remaining_amount` — `budget_amount - spent_amount`
- `percentage_used` — exact decimal percentage
- `status` — `healthy`, `warning` (at/above threshold), or `exceeded`

`warning_threshold_percent` defaults to 80 and is configurable per budget.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/budgets` | Create |
| GET | `/budgets` | List (optional `include_utilization`, `as_of_date`) |
| GET | `/budgets/analytics/utilization` | All active budgets with utilization |
| GET | `/budgets/{id}` | Get one |
| GET | `/budgets/{id}/utilization` | Utilization analytics |
| PATCH | `/budgets/{id}` | Update |
| POST | `/budgets/{id}/archive` | Archive |
