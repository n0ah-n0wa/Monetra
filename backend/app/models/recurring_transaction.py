"""Recurring transaction model."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import MoneyNumeric
from app.models.enum_column import pg_enum
from app.models.enums import RecurringFrequency, TransactionType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.financial_account import FinancialAccount
    from app.models.recurring_transaction_execution import RecurringTransactionExecution
    from app.models.user import User


class RecurringTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recurring_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_recurring_transactions_amount_positive"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_recurring_transactions_date_range",
        ),
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["financial_accounts.id", "financial_accounts.user_id"],
            name="fk_recurring_transactions_account_owner",
        ),
        Index("ix_recurring_transactions_user_id", "user_id"),
        Index(
            "ix_recurring_transactions_next_execution_date",
            "next_execution_date",
        ),
        Index(
            "ix_recurring_transactions_user_id_is_active",
            "user_id",
            "is_active",
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
    transaction_type: Mapped[TransactionType] = mapped_column(
        pg_enum(TransactionType, "transaction_type"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(MoneyNumeric(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    frequency: Mapped[RecurringFrequency] = mapped_column(
        pg_enum(RecurringFrequency, "recurring_frequency"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_execution_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    user: Mapped[User] = relationship(back_populates="recurring_transactions")
    account: Mapped[FinancialAccount] = relationship(
        back_populates="recurring_transactions",
        foreign_keys=[account_id],
        overlaps="user,recurring_transactions",
    )
    category: Mapped[Category] = relationship(
        back_populates="recurring_transactions",
    )
    executions: Mapped[list[RecurringTransactionExecution]] = relationship(
        back_populates="recurring_transaction",
    )

    def __repr__(self) -> str:
        return f"RecurringTransaction(id={self.id!s}, frequency={self.frequency!s})"
