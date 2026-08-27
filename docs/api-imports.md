# CSV Import API

Base path: `/api/v1/imports`

Workflow: **Upload → Validate → Parse → Preview → Confirm → Import → Report**

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/imports` | Upload a CSV (`multipart/form-data`: `file`, `account_id`) → preview job |
| GET | `/imports` | List import jobs (paginated) |
| GET | `/imports/{id}` | Get job status, stats, preview, and row errors |
| POST | `/imports/{id}/confirm` | Confirm a preview job and create transactions |

## CSV format

Required columns:

- `transaction_date` — ISO date `YYYY-MM-DD`
- `transaction_type` — `income` or `expense`
- `amount` — positive decimal
- `description`
- `category` — existing category name (user or system)

Optional columns:

- `external_reference`
- `notes`

Encoding must be UTF-8. File size and row count are limited by settings (`IMPORT_MAX_FILE_BYTES`, `IMPORT_MAX_ROWS`).

## Duplicate detection (deterministic)

1. Prefer `external_reference` when present (scoped to user + account).
2. Otherwise fingerprint: account + date + amount + normalized description (lowercase, collapsed whitespace).
3. Intra-file duplicates are flagged against earlier rows in the same upload.

Preview marks duplicates before confirm. Confirm **re-checks** the live ledger
(under account locks) so rows that became duplicates between preview and confirm
are skipped when `skip_duplicates` is true.

Confirm accepts `{ "skip_duplicates": true }` (default) to skip duplicates, or
`false` to import fingerprint duplicates when allowed. Conflicting
`external_reference` values cannot be force-imported (unique constraint).

Re-confirming a **completed** job is idempotent and returns the same result.

## Stats

Every job reports:

- `total_rows`
- `valid_rows`
- `invalid_rows`
- `imported_rows`
- `skipped_rows`
- `duplicate_rows`

## Atomicity

Confirm runs in a single database transaction with account row locks. On failure the transaction is rolled back and the job is marked `failed` so existing balances and transactions are not partially corrupted.

Uploads are read in bounded chunks (`IMPORT_MAX_FILE_BYTES`). Filenames are sanitized to a `.csv` basename.
