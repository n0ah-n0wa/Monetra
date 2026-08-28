"""CSV import job model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enum_column import pg_enum
from app.models.enums import ImportJobStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.financial_account import FinancialAccount
    from app.models.transaction import Transaction
    from app.models.user import User


class ImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["target_account_id", "user_id"],
            ["financial_accounts.id", "financial_accounts.user_id"],
            name="fk_import_jobs_target_account_owner",
        ),
        Index("ix_import_jobs_user_id", "user_id"),
        Index("ix_import_jobs_user_id_status", "user_id", "status"),
        Index("ix_import_jobs_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ImportJobStatus] = mapped_column(
        pg_enum(ImportJobStatus, "import_job_status"),
        nullable=False,
        default=ImportJobStatus.PENDING,
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="import_jobs")
    target_account: Mapped[FinancialAccount | None] = relationship(
        back_populates="import_jobs",
        foreign_keys=[target_account_id],
        overlaps="user,import_jobs",
    )
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="import_job",
    )

    def __repr__(self) -> str:
        return f"ImportJob(id={self.id!s}, status={self.status!s})"
