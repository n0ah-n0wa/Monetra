"""add user password_changed_at for token invalidation

Revision ID: e6f7a8b901c2
Revises: d5e6f7a8b901
Create Date: 2026-08-27 00:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b901c2"
down_revision: str | None = "d5e6f7a8b901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
