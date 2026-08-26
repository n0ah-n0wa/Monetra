"""Financial account model."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import MoneyNumeric
from app.models.enum_column import pg_enum
from app.models.enums import AccountStatus, AccountType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.financial_goal import FinancialGoal
    from app.models.import_job import ImportJob
    from app.models.recurring_transaction import RecurringTransaction
    from app.models.transaction import Transaction
    from app.models.transfer import Transfer
    from app.models.user import User


class FinancialAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_accounts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name",
            name="uq_financial_accounts_user_id_name",
        ),
        UniqueConstraint(
            "id",
            "user_id",
            name="uq_financial_accounts_id_user_id",
        ),
        Index("ix_financial_accounts_user_id", "user_id"),
        Index("ix_financial_accounts_user_id_status", "user_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        pg_enum(AccountType, "account_type"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(
        MoneyNumeric(),
        nullable=False,
        default=Decimal("0"),
    )
    current_balance: Mapped[Decimal] = mapped_column(
        MoneyNumeric(),
        nullable=False,
        default=Decimal("0"),
    )
    status: Mapped[AccountStatus] = mapped_column(
        pg_enum(AccountStatus, "account_status"),
        nullable=False,
        default=AccountStatus.ACTIVE,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="financial_accounts")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="account",
        foreign_keys="Transaction.account_id",
        overlaps="user,transactions",
    )
    outgoing_transfers: Mapped[list[Transfer]] = relationship(
        back_populates="source_account",
        foreign_keys="Transfer.source_account_id",
        overlaps="user,destination_account,incoming_transfers,outgoing_transfers",
    )
    incoming_transfers: Mapped[list[Transfer]] = relationship(
        back_populates="destination_account",
        foreign_keys="Transfer.destination_account_id",
        overlaps="user,source_account,incoming_transfers,outgoing_transfers",
    )
    recurring_transactions: Mapped[list[RecurringTransaction]] = relationship(
        back_populates="account",
        foreign_keys="RecurringTransaction.account_id",
        overlaps="user,recurring_transactions",
    )
    linked_goals: Mapped[list[FinancialGoal]] = relationship(
        back_populates="linked_account",
        foreign_keys="FinancialGoal.linked_account_id",
        overlaps="user,linked_goals",
    )
    import_jobs: Mapped[list[ImportJob]] = relationship(
        back_populates="target_account",
        foreign_keys="ImportJob.target_account_id",
        overlaps="user,import_jobs",
    )

    def __repr__(self) -> str:
        return f"FinancialAccount(id={self.id!s}, name={self.name!r})"
