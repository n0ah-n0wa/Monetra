"""Add performance indexes for transfer balances, goals, imports, and duplicates.

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c012d3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "f7a8b9c012d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_transfers_source_account_id",
        "transfers",
        ["source_account_id"],
    )
    op.create_index(
        "ix_transfers_destination_account_id",
        "transfers",
        ["destination_account_id"],
    )
    op.create_index(
        "ix_financial_goals_linked_account_id",
        "financial_goals",
        ["linked_account_id"],
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.create_index(
        "ix_import_jobs_user_id_created_at",
        "import_jobs",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_transactions_user_account_date_active",
        "transactions",
        ["user_id", "account_id", "transaction_date"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transactions_user_account_date_active",
        table_name="transactions",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index("ix_import_jobs_user_id_created_at", table_name="import_jobs")
    op.drop_index(
        "ix_financial_goals_linked_account_id",
        table_name="financial_goals",
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.drop_index(
        "ix_transfers_destination_account_id",
        table_name="transfers",
    )
    op.drop_index("ix_transfers_source_account_id", table_name="transfers")
