"""Budget model and category association."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import MoneyNumeric
from app.models.enum_column import pg_enum
from app.models.enums import BudgetPeriod, BudgetScope
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


budget_categories = Table(
    "budget_categories",
    Base.metadata,
    Column(
        "budget_id",
        UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_budgets_amount_positive"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_budgets_date_range",
        ),
        CheckConstraint(
            "warning_threshold_percent BETWEEN 0 AND 100",
            name="ck_budgets_warning_threshold_range",
        ),
        Index("ix_budgets_user_id", "user_id"),
        Index("ix_budgets_user_id_start_date", "user_id", "start_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MoneyNumeric(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    period: Mapped[BudgetPeriod] = mapped_column(
        pg_enum(BudgetPeriod, "budget_period"),
        nullable=False,
    )
    scope: Mapped[BudgetScope] = mapped_column(
        pg_enum(BudgetScope, "budget_scope"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    warning_threshold_percent: Mapped[int] = mapped_column(
        nullable=False,
        default=80,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="budgets")
    categories: Mapped[list[Category]] = relationship(
        secondary=budget_categories,
        back_populates="budgets",
    )

    def __repr__(self) -> str:
        return f"Budget(id={self.id!s}, name={self.name!r})"
