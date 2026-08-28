"""Transfer model."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import ExchangeRateNumeric, MoneyNumeric
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.financial_account import FinancialAccount
    from app.models.user import User


class Transfer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint(
            "source_account_id <> destination_account_id",
            name="ck_transfers_distinct_accounts",
        ),
        CheckConstraint(
            "source_amount > 0",
            name="ck_transfers_source_amount_positive",
        ),
        CheckConstraint(
            "destination_amount > 0",
            name="ck_transfers_destination_amount_positive",
        ),
        CheckConstraint(
            "(source_currency = destination_currency AND exchange_rate IS NULL) OR "
            "(source_currency <> destination_currency AND exchange_rate IS NOT NULL)",
            name="ck_transfers_exchange_rate_consistency",
        ),
        CheckConstraint(
            "(source_currency <> destination_currency) OR "
            "(source_amount = destination_amount)",
            name="ck_transfers_same_currency_amount",
        ),
        ForeignKeyConstraint(
            ["source_account_id", "user_id"],
            ["financial_accounts.id", "financial_accounts.user_id"],
            name="fk_transfers_source_account_owner",
        ),
        ForeignKeyConstraint(
            ["destination_account_id", "user_id"],
            ["financial_accounts.id", "financial_accounts.user_id"],
            name="fk_transfers_destination_account_owner",
        ),
        Index("ix_transfers_user_id", "user_id"),
        Index("ix_transfers_transaction_date", "transaction_date"),
        Index(
            "ix_transfers_user_id_transaction_date",
            "user_id",
            "transaction_date",
        ),
        Index("ix_transfers_source_account_id", "source_account_id"),
        Index("ix_transfers_destination_account_id", "destination_account_id"),
        Index(
            "uq_transfers_user_id_idempotency_key",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    destination_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    source_amount: Mapped[Decimal] = mapped_column(MoneyNumeric(), nullable=False)
    source_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    destination_amount: Mapped[Decimal] = mapped_column(MoneyNumeric(), nullable=False)
    destination_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    exchange_rate: Mapped[Decimal | None] = mapped_column(
        ExchangeRateNumeric(),
        nullable=True,
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="transfers")
    source_account: Mapped[FinancialAccount] = relationship(
        back_populates="outgoing_transfers",
        foreign_keys=[source_account_id],
        overlaps="user,destination_account,incoming_transfers,outgoing_transfers",
    )
    destination_account: Mapped[FinancialAccount] = relationship(
        back_populates="incoming_transfers",
        foreign_keys=[destination_account_id],
        overlaps="user,source_account,incoming_transfers,outgoing_transfers",
    )

    def __repr__(self) -> str:
        return f"Transfer(id={self.id!s}, source={self.source_amount})"
