"""Financial goal model."""

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
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import MoneyNumeric
from app.models.enum_column import pg_enum
from app.models.enums import GoalStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.financial_account import FinancialAccount
    from app.models.user import User


class FinancialGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_financial_goals_target_positive"),
        CheckConstraint(
            "current_amount >= 0",
            name="ck_financial_goals_current_non_negative",
        ),
        ForeignKeyConstraint(
            ["linked_account_id", "user_id"],
            ["financial_accounts.id", "financial_accounts.user_id"],
            name="fk_financial_goals_linked_account_owner",
        ),
        Index("ix_financial_goals_user_id", "user_id"),
        Index("ix_financial_goals_user_id_status", "user_id", "status"),
        Index(
            "ix_financial_goals_linked_account_id",
            "linked_account_id",
            postgresql_where=text("archived_at IS NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(MoneyNumeric(), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        MoneyNumeric(),
        nullable=False,
        default=Decimal("0"),
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    linked_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    status: Mapped[GoalStatus] = mapped_column(
        pg_enum(GoalStatus, "goal_status"),
        nullable=False,
        default=GoalStatus.ACTIVE,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="financial_goals")
    linked_account: Mapped[FinancialAccount | None] = relationship(
        back_populates="linked_goals",
        foreign_keys=[linked_account_id],
        overlaps="user,financial_goals",
    )

    def __repr__(self) -> str:
        return f"FinancialGoal(id={self.id!s}, name={self.name!r})"
