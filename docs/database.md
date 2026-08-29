# Database

Monetra uses **PostgreSQL 16** with **SQLAlchemy 2.x** ORM models and **Alembic** for schema migrations. All monetary columns use PostgreSQL `NUMERIC`; application code uses Python `Decimal`.

## ER diagram

```mermaid
erDiagram
  users ||--o{ financial_accounts : owns
  users ||--o{ categories : owns
  users ||--o{ transactions : owns
  users ||--o{ transfers : owns
  users ||--o{ recurring_transactions : owns
  users ||--o{ budgets : owns
  users ||--o{ financial_goals : owns
  users ||--o{ import_jobs : owns
  users ||--o{ notifications : receives
  users ||--o{ notification_preferences : configures
  users ||--o{ audit_events : generates
  users ||--o{ refresh_tokens : has
  users ||--o{ password_reset_tokens : has

  financial_accounts ||--o{ transactions : records
  financial_accounts ||--o{ transfers : source
  financial_accounts ||--o{ transfers : destination
  financial_accounts ||--o{ recurring_transactions : schedules
  financial_accounts ||--o{ import_jobs : targets
  financial_accounts ||--o{ financial_goals : linked

  categories ||--o{ transactions : classifies
  categories ||--o{ recurring_transactions : classifies
  categories }o--o{ budgets : "budget_categories"

  recurring_transactions ||--o{ recurring_transaction_executions : runs
  recurring_transaction_executions ||--o| transactions : creates

  exchange_rates {
    uuid id PK
    string base_currency
    string quote_currency
    date rate_date
    numeric rate
  }
```

`exchange_rates` is a global reference table (not user-scoped). Rates are keyed by currency pair and date for historical analytics.

## Tables

| Table | Model | Purpose |
|-------|-------|---------|
| `users` | `User` | Accounts, email, password hash, reporting currency |
| `refresh_tokens` | `RefreshToken` | Hashed refresh token sessions |
| `password_reset_tokens` | `PasswordResetToken` | Single-use reset tokens |
| `financial_accounts` | `FinancialAccount` | Cash, bank, savings, credit accounts |
| `categories` | `Category` | Income, expense, universal categories |
| `transactions` | `Transaction` | Income and expense ledger entries |
| `transfers` | `Transfer` | Inter-account transfers |
| `recurring_transactions` | `RecurringTransaction` | Scheduled transaction templates |
| `recurring_transaction_executions` | `RecurringTransactionExecution` | Execution log per schedule run |
| `budgets` | `Budget` | Spending limits by period |
| `budget_categories` | association | Many-to-many budget ↔ category |
| `financial_goals` | `FinancialGoal` | Savings targets |
| `exchange_rates` | `ExchangeRate` | Daily FX snapshots for analytics |
| `import_jobs` | `ImportJob` | CSV import workflow state |
| `notifications` | `Notification` | In-app notifications |
| `notification_preferences` | `NotificationPreference` | Per-type delivery settings |
| `audit_events` | `AuditEvent` | Security and data-change audit log |

Models live in `backend/app/models/`. Enums are defined in `backend/app/models/enums.py`.

## Key constraints

| Rule | Enforcement |
|------|-------------|
| Positive amounts | Check constraints on `transactions.amount`, `transfers.source_amount`, etc. |
| Account ownership | Composite FKs tie `transactions.user_id` to `financial_accounts.user_id` |
| Soft delete | `transactions.deleted_at` — deletes reverse balance impact, row retained |
| Unique account names | Per user: `UNIQUE (user_id, name)` on `financial_accounts` |
| Budget categories | `budget_categories` junction with `ON DELETE CASCADE` from budgets |
| Exchange rates | `UNIQUE (base_currency, quote_currency, rate_date)` |

## Balance invariant

For each financial account:

```text
current_balance = opening_balance
                + sum(income transactions)
                - sum(expense transactions)
                ± transfer effects (source debited, destination credited)
```

Transfers create paired ledger effects on the server. See [api-transactions.md](./api-transactions.md) and [api-transfers.md](./api-transfers.md).

## Migrations

Schema changes **only** through Alembic. The application does not create or alter tables on startup.

```bash
cd backend

# Apply all migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe change"
# Review the generated file, then:
alembic upgrade head
```

Migration files: `backend/alembic/versions/`.

### CI and deployment

- **CI** runs `alembic upgrade head` before backend tests and E2E.
- **Production** (`scripts/deploy-production.sh`) runs migrations explicitly before starting app containers.
- Set `RUN_DB_MIGRATIONS=false` in production after deploy script handles migrations (see `.env.production.example`).

## Connection configuration

| Variable | Example |
|----------|---------|
| `DATABASE_URL` | `postgresql+psycopg://monetra:monetra@localhost:5432/monetra` |

Pool settings (`database_pool_size`, `database_max_overflow`) are configured in `backend/app/core/config.py` with sensible defaults.

## Backup and restore

Production backups use `scripts/backup-database.sh` (pg_dump, retention tiers, optional S3). Restore procedure: [deployment/backup-restore.md](./deployment/backup-restore.md).

Verify restored data:

```bash
python backend/scripts/verify_restored_database.py
```

## Related documentation

- [ADR 004: Database strategy](./adr/004-database-strategy.md)
- [ADR 003: Money representation](./adr/003-money-representation.md)
- [deployment/configuration.md](./deployment/configuration.md) — `POSTGRES_*` and `DATABASE_URL`
