"""Verify financial integrity and migration state of a restored PostgreSQL database.

Run against a non-production restore target:

    DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname \\
      python -m scripts.verify_restored_database

Exit code 0 when all checks pass; non-zero otherwise.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass

from alembic.config import Config
from alembic.script import ScriptDirectory
from app.db.session import dispose_db, get_session_factory, init_db
from app.models.financial_account import FinancialAccount
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from app.services.balance_service import (
    BalanceInvariantError,
    assert_user_balance_invariant,
)
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class VerificationReport:
    user_count: int
    account_count: int
    transaction_count: int
    transfer_count: int
    alembic_revision: str | None
    alembic_heads: tuple[str, ...]
    users_checked: int


def _alembic_config() -> Config:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return Config(os.path.join(root, "alembic.ini"))


def _expected_heads() -> tuple[str, ...]:
    script = ScriptDirectory.from_config(_alembic_config())
    return tuple(script.get_heads())


async def _read_alembic_revision(session: AsyncSession) -> str | None:
    result = await session.scalar(
        text("SELECT version_num FROM alembic_version LIMIT 1")
    )
    if result is None:
        return None
    return str(result)


async def _verify(session: AsyncSession) -> VerificationReport:
    user_count = int(await session.scalar(select(func.count()).select_from(User)) or 0)
    account_count = int(
        await session.scalar(select(func.count()).select_from(FinancialAccount)) or 0,
    )
    transaction_count = int(
        await session.scalar(select(func.count()).select_from(Transaction)) or 0,
    )
    transfer_count = int(
        await session.scalar(select(func.count()).select_from(Transfer)) or 0,
    )
    alembic_revision = await _read_alembic_revision(session)

    users = list((await session.scalars(select(User.id))).all())
    for user_id in users:
        await assert_user_balance_invariant(session, user_id=user_id)

    return VerificationReport(
        user_count=user_count,
        account_count=account_count,
        transaction_count=transaction_count,
        transfer_count=transfer_count,
        alembic_revision=alembic_revision,
        alembic_heads=_expected_heads(),
        users_checked=len(users),
    )


def _validate_migration_state(
    report: VerificationReport,
    *,
    require_head: bool,
) -> list[str]:
    errors: list[str] = []
    if report.alembic_revision is None:
        errors.append("alembic_version table is missing or empty")
        return errors

    script = ScriptDirectory.from_config(_alembic_config())
    if script.get_revision(report.alembic_revision) is None:
        errors.append(
            "restored revision "
            f"{report.alembic_revision!r} is unknown to this codebase",
        )
        return errors

    if require_head and report.alembic_revision not in report.alembic_heads:
        errors.append(
            "restored revision "
            f"{report.alembic_revision!r} is not a current head "
            f"{list(report.alembic_heads)!r}; run `alembic upgrade head`",
        )
    return errors


async def _run(*, require_head: bool) -> int:
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    init_db()
    factory = get_session_factory()
    try:
        async with factory() as session:
            report = await _verify(session)
    except BalanceInvariantError as exc:
        print(f"financial integrity check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        await dispose_db()

    errors = _validate_migration_state(report, require_head=require_head)
    print(
        "restore verification: "
        f"users={report.user_count} "
        f"accounts={report.account_count} "
        f"transactions={report.transaction_count} "
        f"transfers={report.transfer_count} "
        f"alembic={report.alembic_revision} "
        f"users_checked={report.users_checked}",
    )

    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1

    print("restore verification passed")
    return 0


def main() -> int:
    require_head = "--require-head" in sys.argv
    if sys.platform == "win32":
        import selectors

        return asyncio.run(
            _run(require_head=require_head),
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    return asyncio.run(_run(require_head=require_head))


if __name__ == "__main__":
    raise SystemExit(main())
