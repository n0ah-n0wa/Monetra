# CSV Export API

Base path: `/api/v1/exports`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/exports/transactions` | Download owned transactions as CSV |

## Filters

Optional query parameters (same semantics as transaction listing):

- `account_id`
- `category_id`
- `transaction_type` (`income` \| `expense`)
- `date_from` / `date_to`
- `amount_min` / `amount_max`
- `currency`
- `description`
- `sort_by` / `sort_order`

Cross-user `account_id` / `category_id` values return `404`. Soft-deleted transactions are excluded. Row count is capped by `EXPORT_MAX_ROWS`.

## CSV columns

Preserved fields:

- `transaction_date`
- `transaction_type`
- `amount` (original ledger amount, 4 decimal places)
- `currency`
- `description`
- `category` (name)
- `account` (name)

UTF-8 CSV with standard quoting/escaping. Empty result sets still include the header row.

Text fields that look like spreadsheet formulas (`=`, `+`, `-`, `@`, leading tab/CR) are neutralized with a leading `'` to mitigate CSV injection when opened in Excel/LibreOffice.
