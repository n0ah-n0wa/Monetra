# Recurring Transactions API

Base path: `/api/v1/recurring-transactions`

Recurring transactions define a schedule that materializes income or expense transactions on due dates. Execution is idempotent: each `(recurring_transaction_id, execution_date)` pair is recorded at most once.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/recurring-transactions` | Create a recurring definition |
| GET | `/recurring-transactions` | List (paginated, optional `is_active`) |
| GET | `/recurring-transactions/{id}` | Get one |
| PATCH | `/recurring-transactions/{id}` | Update |
| POST | `/recurring-transactions/{id}/archive` | Deactivate (`is_active=false`) |
| POST | `/recurring-transactions/process-due` | Execute due schedules for the current user |

## Schedules

Supported frequencies: `daily`, `weekly`, `biweekly`, `monthly`, `quarterly`, `yearly`.

- `start_date` — first execution date; initial `next_execution_date`.
- `end_date` (optional) — last date on which execution may occur.
- Monthly/quarterly/yearly schedules preserve the anchor day from `start_date`, clamping to the last day of shorter months (e.g. Jan 31 → Feb 28/29).

## Execution

`POST /recurring-transactions/process-due` accepts an optional body:

```json
{ "as_of_date": "2026-01-15" }
```

When omitted, today's UTC date is used. All due dates up to and including `as_of_date` are processed (catch-up for missed runs). Each run:

1. Creates a ledger execution record (unique per date).
2. Creates a normal transaction and updates the account balance.
3. Advances `next_execution_date`.

Re-running for the same dates is a no-op (duplicate prevention via the execution ledger).

The service layer also exposes `process_due_recurring_transactions()` for a future background worker across all users.

## Errors

| Code | HTTP | When |
|------|------|------|
| `RECURRING_TRANSACTION_NOT_FOUND` | 404 | Unknown or other user's id |
| `ACCOUNT_ARCHIVED` | 422 | Archived account |
| `CATEGORY_ARCHIVED` | 422 | Archived category |
| `CATEGORY_TYPE_MISMATCH` | 422 | Category incompatible with type |
| `INVALID_DATE_RANGE` | 422 | `end_date` before `start_date` |
