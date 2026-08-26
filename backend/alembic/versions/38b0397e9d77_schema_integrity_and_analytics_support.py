"""schema integrity and analytics support

Revision ID: 38b0397e9d77
Revises: 54225e4cf9db
Create Date: 2026-08-26 21:35:11.279054

Adds non-destructive integrity constraints, analytics indexes, and supporting
tables. Existing rows receive reporting_currency='USD'. No data is deleted.
Downgrade removes added constraints/columns/tables in reverse dependency order.
Legacy single-column account FKs are dropped during upgrade when present; downgrade
does not recreate them because they may still exist from the initial migration.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "38b0397e9d77"
down_revision: str | None = "54225e4cf9db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXCHANGE_RATE_NUMERIC = sa.Numeric(precision=19, scale=8)


def upgrade() -> None:
    # Drop legacy single-column account FKs before replacing them with composite
    # ownership constraints. Safe on empty/dev databases; existing rows must
    # already satisfy user/account ownership or upgrade will fail.
    op.execute(
        "ALTER TABLE import_jobs "
        "DROP CONSTRAINT IF EXISTS fk_import_jobs_target_account_id",
    )
    op.drop_constraint(
        "financial_goals_linked_account_id_fkey",
        "financial_goals",
        type_="foreignkey",
    )
    op.drop_constraint(
        "recurring_transactions_account_id_fkey",
        "recurring_transactions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "transactions_account_id_fkey",
        "transactions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "transfers_destination_account_id_fkey",
        "transfers",
        type_="foreignkey",
    )
    op.drop_constraint(
        "transfers_source_account_id_fkey",
        "transfers",
        type_="foreignkey",
    )

    op.create_table(
        "exchange_rates",
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", EXCHANGE_RATE_NUMERIC, nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "base_currency <> quote_currency",
            name="ck_exchange_rates_distinct_currencies",
        ),
        sa.CheckConstraint("rate > 0", name="ck_exchange_rates_rate_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "base_currency",
            "quote_currency",
            "rate_date",
            name="uq_exchange_rates_pair_date",
        ),
    )
    op.create_index(
        "ix_exchange_rates_pair_rate_date",
        "exchange_rates",
        ["base_currency", "quote_currency", "rate_date"],
        unique=False,
    )
    op.create_index("ix_exchange_rates_rate_date", "exchange_rates", ["rate_date"])

    op.create_table(
        "recurring_transaction_executions",
        sa.Column("recurring_transaction_id", sa.UUID(), nullable=False),
        sa.Column("execution_date", sa.Date(), nullable=False),
        sa.Column("transaction_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["recurring_transaction_id"],
            ["recurring_transactions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recurring_transaction_id",
            "execution_date",
            name="uq_recurring_executions_recurring_date",
        ),
    )
    op.create_index(
        "ix_recurring_executions_recurring_transaction_id",
        "recurring_transaction_executions",
        ["recurring_transaction_id"],
    )

    op.create_check_constraint(
        "ck_budgets_date_range",
        "budgets",
        "end_date IS NULL OR end_date >= start_date",
    )
    op.create_check_constraint(
        "ck_budgets_warning_threshold_range",
        "budgets",
        "warning_threshold_percent BETWEEN 0 AND 100",
    )
    op.create_unique_constraint(
        "uq_financial_accounts_id_user_id",
        "financial_accounts",
        ["id", "user_id"],
    )

    op.add_column(
        "users",
        sa.Column(
            "reporting_currency",
            sa.String(length=3),
            nullable=False,
            server_default="USD",
        ),
    )
    op.alter_column("users", "reporting_currency", server_default=None)

    op.add_column(
        "import_jobs",
        sa.Column("target_account_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_import_jobs_user_id_status",
        "import_jobs",
        ["user_id", "status"],
    )
    op.create_foreign_key(
        "fk_import_jobs_target_account_owner",
        "import_jobs",
        "financial_accounts",
        ["target_account_id", "user_id"],
        ["id", "user_id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_financial_goals_linked_account_owner",
        "financial_goals",
        "financial_accounts",
        ["linked_account_id", "user_id"],
        ["id", "user_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_recurring_transactions_account_owner",
        "recurring_transactions",
        "financial_accounts",
        ["account_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_recurring_transactions_date_range",
        "recurring_transactions",
        "end_date IS NULL OR end_date >= start_date",
    )

    op.add_column(
        "transactions",
        sa.Column("import_job_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("external_reference", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_transactions_user_id_transaction_date_active",
        "transactions",
        ["user_id", "transaction_date"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_transactions_user_id_type_date_active",
        "transactions",
        ["user_id", "transaction_type", "transaction_date"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_transactions_import_external_reference",
        "transactions",
        ["user_id", "account_id", "external_reference"],
        unique=True,
        postgresql_where=sa.text(
            "external_reference IS NOT NULL AND deleted_at IS NULL",
        ),
    )
    op.create_foreign_key(
        "fk_transactions_import_job_id",
        "transactions",
        "import_jobs",
        ["import_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_transactions_account_owner",
        "transactions",
        "financial_accounts",
        ["account_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "transfers",
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_transfers_user_id_idempotency_key",
        "transfers",
        ["user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_foreign_key(
        "fk_transfers_destination_account_owner",
        "transfers",
        "financial_accounts",
        ["destination_account_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_transfers_source_account_owner",
        "transfers",
        "financial_accounts",
        ["source_account_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_transfers_same_currency_amount",
        "transfers",
        "(source_currency <> destination_currency) OR "
        "(source_amount = destination_amount)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_transfers_same_currency_amount", "transfers", type_="check")
    op.drop_constraint(
        "fk_transfers_source_account_owner",
        "transfers",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_transfers_destination_account_owner",
        "transfers",
        type_="foreignkey",
    )
    op.drop_index(
        "uq_transfers_user_id_idempotency_key",
        table_name="transfers",
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.drop_column("transfers", "idempotency_key")

    op.drop_constraint(
        "fk_transactions_account_owner",
        "transactions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_transactions_import_job_id",
        "transactions",
        type_="foreignkey",
    )
    op.drop_index(
        "uq_transactions_import_external_reference",
        table_name="transactions",
        postgresql_where=sa.text(
            "external_reference IS NOT NULL AND deleted_at IS NULL",
        ),
    )
    op.drop_index(
        "ix_transactions_user_id_type_date_active",
        table_name="transactions",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_transactions_user_id_transaction_date_active",
        table_name="transactions",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_column("transactions", "external_reference")
    op.drop_column("transactions", "import_job_id")

    op.drop_constraint(
        "ck_recurring_transactions_date_range",
        "recurring_transactions",
        type_="check",
    )
    op.drop_constraint(
        "fk_recurring_transactions_account_owner",
        "recurring_transactions",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_financial_goals_linked_account_owner",
        "financial_goals",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_import_jobs_target_account_owner",
        "import_jobs",
        type_="foreignkey",
    )
    op.drop_index("ix_import_jobs_user_id_status", table_name="import_jobs")
    op.drop_column("import_jobs", "target_account_id")

    op.drop_column("users", "reporting_currency")

    op.drop_constraint(
        "uq_financial_accounts_id_user_id",
        "financial_accounts",
        type_="unique",
    )
    op.drop_constraint(
        "ck_budgets_warning_threshold_range",
        "budgets",
        type_="check",
    )
    op.drop_constraint("ck_budgets_date_range", "budgets", type_="check")

    op.drop_index(
        "ix_recurring_executions_recurring_transaction_id",
        table_name="recurring_transaction_executions",
    )
    op.drop_table("recurring_transaction_executions")

    op.drop_index("ix_exchange_rates_rate_date", table_name="exchange_rates")
    op.drop_index("ix_exchange_rates_pair_rate_date", table_name="exchange_rates")
    op.drop_table("exchange_rates")
