"""Balance reconciliation service."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.balance import balances_match
from app.repositories import balance_repository as balance_repo


class BalanceInvariantError(Exception):
    """Raised when cached account balance diverges from the ledger."""

    def __init__(
        self,
        *,
        account_id: uuid.UUID,
        cached_balance: Decimal,
        expected_balance: Decimal,
    ) -> None:
        self.account_id = account_id
        self.cached_balance = cached_balance
        self.expected_balance = expected_balance
        super().__init__(
            f"Balance drift on account {account_id}: "
            f"cached={cached_balance} expected={expected_balance}",
        )


async def assert_user_balance_invariant(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> None:
    """Verify all user accounts satisfy the financial balance invariant."""
    for account, cached, expected in await balance_repo.reconcile_user_accounts(
        session,
        user_id=user_id,
    ):
        if not balances_match(cached, expected):
            raise BalanceInvariantError(
                account_id=account.id,
                cached_balance=cached,
                expected_balance=expected,
            )
