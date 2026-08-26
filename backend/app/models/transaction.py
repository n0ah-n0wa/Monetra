"""Transaction model."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import MoneyNumeric
from app.models.enum_column import pg_enum
from app.models.enums import TransactionType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.financial_account import FinancialAccount
    from app.models.import_job import ImportJob
    from app.models.recurring_transaction_execution import RecurringTransactionExecution
    from app.models.user import User


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["financial_accounts.id", "financial_accounts.user_id"],
            name="fk_transactions_account_owner",
        ),
        Index("ix_transactions_user_id", "user_id"),
        Index("ix_transactions_account_id", "account_id"),
        Index("ix_transactions_category_id", "category_id"),
        Index("ix_transactions_transaction_date", "transaction_date"),
        Index(
            "ix_transactions_user_id_transaction_date",
            "user_id",
            "transaction_date",
        ),
        Index(
            "ix_transactions_user_id_category_id_transaction_date",
            "user_id",
            "category_id",
            "transaction_date",
        ),
        Index(
            "ix_transactions_user_id_transaction_date_active",
            "user_id",
            "transaction_date",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_transactions_user_id_type_date_active",
            "user_id",
            "transaction_type",
            "transaction_date",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_transactions_import_external_reference",
            "user_id",
            "account_id",
            "external_reference",
            unique=True,
            postgresql_where=text(
                "external_reference IS NOT NULL AND deleted_at IS NULL",
            ),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        pg_enum(TransactionType, "transaction_type"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(MoneyNumeric(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="transactions")
    account: Mapped[FinancialAccount] = relationship(
        back_populates="transactions",
        foreign_keys=[account_id],
        overlaps="user,financial_accounts",
    )
    category: Mapped[Category] = relationship(back_populates="transactions")
    import_job: Mapped[ImportJob | None] = relationship(back_populates="transactions")
    recurring_execution: Mapped[RecurringTransactionExecution | None] = relationship(
        back_populates="transaction",
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"Transaction(id={self.id!s}, type={self.transaction_type!s}, "
            f"amount={self.amount})"
        )
