"""initial domain schema

Revision ID: 54225e4cf9db
Revises:
Create Date: 2026-08-26 21:21:59.473870

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "54225e4cf9db"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY_NUMERIC = sa.Numeric(precision=19, scale=4)
EXCHANGE_RATE_NUMERIC = sa.Numeric(precision=19, scale=8)

audit_action_enum = postgresql.ENUM(
    "created",
    "updated",
    "deleted",
    "archived",
    "import_executed",
    name="audit_action",
    create_type=False,
)
budget_period_enum = postgresql.ENUM(
    "weekly",
    "monthly",
    "yearly",
    "custom",
    name="budget_period",
    create_type=False,
)
budget_scope_enum = postgresql.ENUM(
    "category",
    "overall",
    name="budget_scope",
    create_type=False,
)
category_type_enum = postgresql.ENUM(
    "income",
    "expense",
    "universal",
    name="category_type",
    create_type=False,
)
category_status_enum = postgresql.ENUM(
    "active",
    "archived",
    name="category_status",
    create_type=False,
)
account_type_enum = postgresql.ENUM(
    "cash",
    "bank",
    "savings",
    "credit_card",
    "digital_wallet",
    name="account_type",
    create_type=False,
)
account_status_enum = postgresql.ENUM(
    "active",
    "archived",
    name="account_status",
    create_type=False,
)
import_job_status_enum = postgresql.ENUM(
    "pending",
    "preview",
    "processing",
    "completed",
    "failed",
    name="import_job_status",
    create_type=False,
)
notification_type_enum = postgresql.ENUM(
    "budget_warning",
    "budget_exceeded",
    "recurring_created",
    "goal_milestone",
    "import_completed",
    "import_failed",
    "general",
    name="notification_type",
    create_type=False,
)
goal_status_enum = postgresql.ENUM(
    "active",
    "completed",
    "archived",
    name="goal_status",
    create_type=False,
)
transaction_type_enum = postgresql.ENUM(
    "income",
    "expense",
    name="transaction_type",
    create_type=False,
)
recurring_frequency_enum = postgresql.ENUM(
    "daily",
    "weekly",
    "biweekly",
    "monthly",
    "quarterly",
    "yearly",
    name="recurring_frequency",
    create_type=False,
)

DOMAIN_ENUMS: tuple[postgresql.ENUM, ...] = (
    audit_action_enum,
    budget_period_enum,
    budget_scope_enum,
    category_type_enum,
    category_status_enum,
    account_type_enum,
    account_status_enum,
    import_job_status_enum,
    notification_type_enum,
    goal_status_enum,
    transaction_type_enum,
    recurring_frequency_enum,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in DOMAIN_ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "audit_events",
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("action", audit_action_enum, nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"], unique=False)
    op.create_index(
        "ix_audit_events_created_at",
        "audit_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_entity_type_entity_id",
        "audit_events",
        ["entity_type", "entity_id"],
        unique=False,
    )
    op.create_table(
        "budgets",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("amount", MONEY_NUMERIC, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("period", budget_period_enum, nullable=False),
        sa.Column("scope", budget_scope_enum, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("warning_threshold_percent", sa.Integer(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("amount > 0", name="ck_budgets_amount_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"], unique=False)
    op.create_index(
        "ix_budgets_user_id_start_date",
        "budgets",
        ["user_id", "start_date"],
        unique=False,
    )
    op.create_table(
        "categories",
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category_type", category_type_enum, nullable=False),
        sa.Column("icon", sa.String(length=64), nullable=True),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("status", category_status_enum, nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
            "(is_system = true AND user_id IS NULL) OR "
            "(is_system = false AND user_id IS NOT NULL)",
            name="ck_categories_system_owner",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"], unique=False)
    op.create_index(
        "ix_categories_user_id_status",
        "categories",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_categories_system_name_type",
        "categories",
        ["name", "category_type"],
        unique=True,
        postgresql_where=sa.text("is_system = true"),
    )
    op.create_index(
        "uq_categories_user_name_type",
        "categories",
        ["user_id", "name", "category_type"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_table(
        "financial_accounts",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("account_type", account_type_enum, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("opening_balance", MONEY_NUMERIC, nullable=False),
        sa.Column("current_balance", MONEY_NUMERIC, nullable=False),
        sa.Column("status", account_status_enum, nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_financial_accounts_user_id_name"),
    )
    op.create_index(
        "ix_financial_accounts_user_id",
        "financial_accounts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_financial_accounts_user_id_status",
        "financial_accounts",
        ["user_id", "status"],
        unique=False,
    )
    op.create_table(
        "import_jobs",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("status", import_job_status_enum, nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False),
        sa.Column("invalid_rows", sa.Integer(), nullable=False),
        sa.Column("imported_rows", sa.Integer(), nullable=False),
        sa.Column("skipped_rows", sa.Integer(), nullable=False),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False),
        sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_jobs_user_id", "import_jobs", ["user_id"], unique=False)
    op.create_table(
        "notifications",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("notification_type", notification_type_enum, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index(
        "ix_notifications_user_id_is_read",
        "notifications",
        ["user_id", "is_read"],
        unique=False,
    )
    op.create_table(
        "budget_categories",
        sa.Column("budget_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("budget_id", "category_id"),
    )
    op.create_table(
        "financial_goals",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("target_amount", MONEY_NUMERIC, nullable=False),
        sa.Column("current_amount", MONEY_NUMERIC, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("linked_account_id", sa.UUID(), nullable=True),
        sa.Column("status", goal_status_enum, nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
            "current_amount >= 0",
            name="ck_financial_goals_current_non_negative",
        ),
        sa.CheckConstraint("target_amount > 0", name="ck_financial_goals_target_positive"),
        sa.ForeignKeyConstraint(
            ["linked_account_id"],
            ["financial_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_financial_goals_user_id",
        "financial_goals",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_financial_goals_user_id_status",
        "financial_goals",
        ["user_id", "status"],
        unique=False,
    )
    op.create_table(
        "recurring_transactions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("transaction_type", transaction_type_enum, nullable=False),
        sa.Column("amount", MONEY_NUMERIC, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("frequency", recurring_frequency_enum, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("next_execution_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
            "amount > 0",
            name="ck_recurring_transactions_amount_positive",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["financial_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recurring_transactions_next_execution_date",
        "recurring_transactions",
        ["next_execution_date"],
        unique=False,
    )
    op.create_index(
        "ix_recurring_transactions_user_id",
        "recurring_transactions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_recurring_transactions_user_id_is_active",
        "recurring_transactions",
        ["user_id", "is_active"],
        unique=False,
    )
    op.create_table(
        "transactions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("transaction_type", transaction_type_enum, nullable=False),
        sa.Column("amount", MONEY_NUMERIC, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["financial_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"], unique=False)
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"], unique=False)
    op.create_index(
        "ix_transactions_transaction_date",
        "transactions",
        ["transaction_date"],
        unique=False,
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"], unique=False)
    op.create_index(
        "ix_transactions_user_id_category_id_transaction_date",
        "transactions",
        ["user_id", "category_id", "transaction_date"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_user_id_transaction_date",
        "transactions",
        ["user_id", "transaction_date"],
        unique=False,
    )
    op.create_table(
        "transfers",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_account_id", sa.UUID(), nullable=False),
        sa.Column("destination_account_id", sa.UUID(), nullable=False),
        sa.Column("source_amount", MONEY_NUMERIC, nullable=False),
        sa.Column("source_currency", sa.String(length=3), nullable=False),
        sa.Column("destination_amount", MONEY_NUMERIC, nullable=False),
        sa.Column("destination_currency", sa.String(length=3), nullable=False),
        sa.Column("exchange_rate", EXCHANGE_RATE_NUMERIC, nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            "(source_currency = destination_currency AND exchange_rate IS NULL) OR "
            "(source_currency <> destination_currency AND exchange_rate IS NOT NULL)",
            name="ck_transfers_exchange_rate_consistency",
        ),
        sa.CheckConstraint(
            "destination_amount > 0",
            name="ck_transfers_destination_amount_positive",
        ),
        sa.CheckConstraint(
            "source_account_id <> destination_account_id",
            name="ck_transfers_distinct_accounts",
        ),
        sa.CheckConstraint("source_amount > 0", name="ck_transfers_source_amount_positive"),
        sa.ForeignKeyConstraint(
            ["destination_account_id"],
            ["financial_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_account_id"],
            ["financial_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transfers_transaction_date",
        "transfers",
        ["transaction_date"],
        unique=False,
    )
    op.create_index("ix_transfers_user_id", "transfers", ["user_id"], unique=False)
    op.create_index(
        "ix_transfers_user_id_transaction_date",
        "transfers",
        ["user_id", "transaction_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transfers_user_id_transaction_date", table_name="transfers")
    op.drop_index("ix_transfers_user_id", table_name="transfers")
    op.drop_index("ix_transfers_transaction_date", table_name="transfers")
    op.drop_table("transfers")
    op.drop_index("ix_transactions_user_id_transaction_date", table_name="transactions")
    op.drop_index(
        "ix_transactions_user_id_category_id_transaction_date",
        table_name="transactions",
    )
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_index("ix_transactions_transaction_date", table_name="transactions")
    op.drop_index("ix_transactions_category_id", table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index(
        "ix_recurring_transactions_user_id_is_active",
        table_name="recurring_transactions",
    )
    op.drop_index("ix_recurring_transactions_user_id", table_name="recurring_transactions")
    op.drop_index(
        "ix_recurring_transactions_next_execution_date",
        table_name="recurring_transactions",
    )
    op.drop_table("recurring_transactions")
    op.drop_index("ix_financial_goals_user_id_status", table_name="financial_goals")
    op.drop_index("ix_financial_goals_user_id", table_name="financial_goals")
    op.drop_table("financial_goals")
    op.drop_table("budget_categories")
    op.drop_index("ix_notifications_user_id_is_read", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_import_jobs_user_id", table_name="import_jobs")
    op.drop_table("import_jobs")
    op.drop_index("ix_financial_accounts_user_id_status", table_name="financial_accounts")
    op.drop_index("ix_financial_accounts_user_id", table_name="financial_accounts")
    op.drop_table("financial_accounts")
    op.drop_index(
        "uq_categories_user_name_type",
        table_name="categories",
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_categories_system_name_type",
        table_name="categories",
        postgresql_where=sa.text("is_system = true"),
    )
    op.drop_index("ix_categories_user_id_status", table_name="categories")
    op.drop_index("ix_categories_user_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_budgets_user_id_start_date", table_name="budgets")
    op.drop_index("ix_budgets_user_id", table_name="budgets")
    op.drop_table("budgets")
    op.drop_index("ix_audit_events_entity_type_entity_id", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in reversed(DOMAIN_ENUMS):
        enum_type.drop(bind, checkfirst=True)
