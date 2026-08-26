"""Execution ledger for idempotent recurring transaction processing."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.recurring_transaction import RecurringTransaction
    from app.models.transaction import Transaction


class RecurringTransactionExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recurring_transaction_executions"
    __table_args__ = (
        UniqueConstraint(
            "recurring_transaction_id",
            "execution_date",
            name="uq_recurring_executions_recurring_date",
        ),
        Index(
            "ix_recurring_executions_recurring_transaction_id",
            "recurring_transaction_id",
        ),
    )

    recurring_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recurring_transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    recurring_transaction: Mapped[RecurringTransaction] = relationship(
        back_populates="executions",
    )
    transaction: Mapped[Transaction | None] = relationship(
        back_populates="recurring_execution",
    )

    def __repr__(self) -> str:
        return (
            f"RecurringTransactionExecution(recurring="
            f"{self.recurring_transaction_id!s}, date={self.execution_date})"
        )
