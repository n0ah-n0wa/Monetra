"""User account model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.audit_event import AuditEvent
    from app.models.budget import Budget
    from app.models.category import Category
    from app.models.financial_account import FinancialAccount
    from app.models.financial_goal import FinancialGoal
    from app.models.import_job import ImportJob
    from app.models.notification import Notification
    from app.models.password_reset_token import PasswordResetToken
    from app.models.recurring_transaction import RecurringTransaction
    from app.models.refresh_token import RefreshToken
    from app.models.transaction import Transaction
    from app.models.transfer import Transfer


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    reporting_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    financial_accounts: Mapped[list[FinancialAccount]] = relationship(
        back_populates="user",
    )
    categories: Mapped[list[Category]] = relationship(back_populates="user")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="user")
    transfers: Mapped[list[Transfer]] = relationship(back_populates="user")
    recurring_transactions: Mapped[list[RecurringTransaction]] = relationship(
        back_populates="user",
    )
    budgets: Mapped[list[Budget]] = relationship(back_populates="user")
    financial_goals: Mapped[list[FinancialGoal]] = relationship(
        back_populates="user",
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="user")
    import_jobs: Mapped[list[ImportJob]] = relationship(back_populates="user")
    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="actor",
        foreign_keys="AuditEvent.actor_id",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user",
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!s}, email={self.email!r})"
