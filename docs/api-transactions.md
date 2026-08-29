# Transactions API

Authenticated endpoints under `/api/v1/transactions`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/transactions` | Create income or expense transaction |
| `GET` | `/transactions` | List transactions (filtered, sorted, paginated) |
| `GET` | `/transactions/{id}` | Retrieve a transaction |
| `PATCH` | `/transactions/{id}` | Update a transaction |
| `DELETE` | `/transactions/{id}` | Soft-delete a transaction |

Transactions are soft-deleted (`deleted_at` set) to preserve ledger integrity. Deleting a transaction reverses its balance effect on the account.

## Balance invariant

For each account:

```text
current_balance = opening_balance + income - expenses ± transfer effects
```

Balance updates are applied atomically with transaction create, update, and delete operations using exact `Decimal` arithmetic. Transfers adjust both source and destination account balances via the transfers service.

## Create body

```json
{
  "account_id": "uuid",
  "category_id": "uuid",
  "transaction_type": "expense",
  "amount": "125.5000",
  "description": "Groceries",
  "transaction_date": "2026-01-15",
  "notes": "optional"
}
```

Amounts must be positive. Currency is taken from the account. Category type must match the transaction type (universal categories are allowed for both).

## List query parameters

- `page`, `page_size` — pagination (default page size 20, max 100)
- `account_id`, `category_id`, `transaction_type`
- `date_from`, `date_to` — inclusive date range (`YYYY-MM-DD`)
- `amount_min`, `amount_max`
- `currency` — three-letter code
- `description` — case-insensitive partial match
- `sort_by` — `transaction_date` (default), `amount`, `created_at`, `description`
- `sort_order` — `asc` or `desc` (default `desc`)

## Errors

| Code | HTTP | Meaning |
|------|------|---------|
| `TRANSACTION_NOT_FOUND` | 404 | Missing or deleted transaction |
| `ACCOUNT_NOT_FOUND` | 404 | Account not owned by user |
| `INVALID_AMOUNT` | 422 | Amount must be greater than zero |
| `CATEGORY_TYPE_MISMATCH` | 422 | Category incompatible with transaction type |
| `ACCOUNT_ARCHIVED` | 422 | Cannot post to archived account |
| `CATEGORY_ARCHIVED` | 422 | Cannot use archived category |
| `INVALID_DATE_RANGE` | 422 | `date_from` after `date_to` |
| `INVALID_AMOUNT_RANGE` | 422 | `amount_min` greater than `amount_max` |
