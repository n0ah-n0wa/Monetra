# Transfers API

Authenticated endpoints under `/api/v1/transfers`.

Transfers are stored separately from income/expense transactions and must not be counted as income or expenses in analytics.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/transfers` | Create a transfer (`201` new, `200` idempotent replay) |
| `GET` | `/transfers` | List transfers (paginated) |
| `GET` | `/transfers/{id}` | Retrieve a transfer |

## Create body

Same currency:

```json
{
  "source_account_id": "uuid",
  "destination_account_id": "uuid",
  "source_amount": "150.2500",
  "transaction_date": "2026-02-10",
  "description": "Move to savings",
  "idempotency_key": "optional-client-key"
}
```

Cross currency (provide `exchange_rate` and/or `destination_amount`):

```json
{
  "source_account_id": "uuid",
  "destination_account_id": "uuid",
  "source_amount": "200.0000",
  "exchange_rate": "0.85000000",
  "transaction_date": "2026-02-10"
}
```

The exchange rate means **1 unit of source currency = rate units of destination currency**.

## Atomicity

Transfer creation locks source and destination accounts, validates balances, updates both account balances, and inserts the transfer record in a single database transaction.

## Idempotency

When `idempotency_key` is supplied, retries with the same payload return the original transfer (`200`). Reusing the key with a different payload returns `409 IDEMPOTENCY_KEY_CONFLICT`.

## Errors

| Code | HTTP | Meaning |
|------|------|---------|
| `SAME_ACCOUNT_TRANSFER` | 422 | Source and destination must differ |
| `INSUFFICIENT_BALANCE` | 422 | Source account lacks funds |
| `ACCOUNT_NOT_FOUND` | 404 | Account not owned by user |
| `ACCOUNT_ARCHIVED` | 422 | Archived account cannot participate |
| `TRANSFER_AMOUNT_MISMATCH` | 422 | Amounts/rate inconsistent |
| `INVALID_EXCHANGE_RATE` | 422 | Rate invalid or present for same currency |
| `IDEMPOTENCY_KEY_CONFLICT` | 409 | Key reused with different payload |
| `TRANSFER_NOT_FOUND` | 404 | Transfer not found |
