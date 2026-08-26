"""Database schema and model integration tests."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from app.models import (
    AuditEvent,
    Budget,
    Category,
    ExchangeRate,
    FinancialAccount,
    FinancialGoal,
    ImportJob,
    Notification,
    RecurringTransaction,
    RecurringTransactionExecution,
    Transaction,
    Transfer,
    User,
)
from app.models.enums import (
    AccountType,
    AuditAction,
    BudgetPeriod,
    BudgetScope,
    CategoryType,
    GoalStatus,
    ImportJobStatus,
    NotificationType,
    RecurringFrequency,
    TransactionType,
)
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.db.conftest import make_transaction

EXPECTED_TABLES = {
    "users",
    "financial_accounts",
    "categories",
    "transactions",
    "transfers",
    "recurring_transactions",
    "recurring_transaction_executions",
    "budgets",
    "budget_categories",
    "financial_goals",
    "notifications",
    "import_jobs",
    "audit_events",
    "exchange_rates",
    "refresh_tokens",
    "password_reset_tokens",
}


@pytest.mark.asyncio
async def test_schema_tables_exist(db_engine) -> None:
    async with db_engine.connect() as connection:
        table_names = await connection.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names()),
        )
    assert EXPECTED_TABLES.issubset(table_names)


@pytest.mark.asyncio
async def test_money_columns_use_numeric(db_engine) -> None:
    query = text(
        """
        SELECT table_name, column_name, data_type, numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_name IN (
            'amount',
            'opening_balance',
            'current_balance',
            'target_amount',
            'current_amount',
            'source_amount',
            'destination_amount',
            'exchange_rate'
          )
        ORDER BY table_name, column_name
        """
    )
    async with db_engine.connect() as connection:
        rows = (await connection.execute(query)).mappings().all()

    assert rows, "expected monetary columns in the schema"
    for row in rows:
        assert row["data_type"] == "numeric"
        if row["column_name"] == "exchange_rate":
            assert row["numeric_precision"] == 19
            assert row["numeric_scale"] == 8
        else:
            assert row["numeric_precision"] == 19
            assert row["numeric_scale"] == 4


@pytest.mark.asyncio
async def test_user_email_must_be_unique(db_session: AsyncSession) -> None:
    changed_at = datetime.now(UTC)
    db_session.add(
        User(
            email="dup@example.com",
            password_hash="hash-a",
            password_changed_at=changed_at,
        ),
    )
    await db_session.flush()
    db_session.add(
        User(
            email="dup@example.com",
            password_hash="hash-b",
            password_changed_at=changed_at,
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_account_name_unique_per_user(
    db_session: AsyncSession,
    user: User,
) -> None:
    db_session.add(
        FinancialAccount(
            user_id=user.id,
            name="Wallet",
            account_type=AccountType.CASH,
            currency="USD",
        ),
    )
    await db_session.flush()
    db_session.add(
        FinancialAccount(
            user_id=user.id,
            name="Wallet",
            account_type=AccountType.BANK,
            currency="EUR",
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_system_category_requires_null_owner(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        Category(
            user_id=None,
            name="System Income",
            category_type=CategoryType.INCOME,
            is_system=True,
        ),
    )
    await db_session.flush()

    db_session.add(
        Category(
            user_id=None,
            name="Broken",
            category_type=CategoryType.EXPENSE,
            is_system=False,
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_user_category_requires_owner(
    db_session: AsyncSession,
    user: User,
) -> None:
    db_session.add(
        Category(
            user_id=user.id,
            name="Personal",
            category_type=CategoryType.EXPENSE,
            is_system=False,
        ),
    )
    await db_session.flush()

    db_session.add(
        Category(
            user_id=None,
            name="Invalid User Category",
            category_type=CategoryType.EXPENSE,
            is_system=False,
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_category_name_unique_for_user(
    db_session: AsyncSession,
    user: User,
    expense_category: Category,
) -> None:
    db_session.add(
        Category(
            user_id=user.id,
            name=expense_category.name,
            category_type=CategoryType.EXPENSE,
            is_system=False,
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_system_category_name_unique(
    db_session: AsyncSession,
    system_category: Category,
) -> None:
    db_session.add(
        Category(
            user_id=None,
            name=system_category.name,
            category_type=CategoryType.UNIVERSAL,
            is_system=True,
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_transaction_amount_must_be_positive(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    expense_category: Category,
) -> None:
    db_session.add(
        Transaction(
            user_id=user.id,
            account_id=account.id,
            category_id=expense_category.id,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal("0"),
            currency="USD",
            description="Zero amount",
            transaction_date=date(2026, 1, 1),
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_transfer_requires_distinct_accounts(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
) -> None:
    db_session.add(
        Transfer(
            user_id=user.id,
            source_account_id=account.id,
            destination_account_id=account.id,
            source_amount=Decimal("10.0000"),
            source_currency="USD",
            destination_amount=Decimal("10.0000"),
            destination_currency="USD",
            transaction_date=date(2026, 1, 1),
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_transfer_exchange_rate_consistency(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    other_account: FinancialAccount,
) -> None:
    db_session.add(
        Transfer(
            user_id=user.id,
            source_account_id=account.id,
            destination_account_id=other_account.id,
            source_amount=Decimal("10.0000"),
            source_currency="USD",
            destination_amount=Decimal("10.0000"),
            destination_currency="EUR",
            exchange_rate=None,
            transaction_date=date(2026, 1, 1),
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_same_currency_transfer_omits_exchange_rate(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    other_account: FinancialAccount,
) -> None:
    db_session.add(
        Transfer(
            user_id=user.id,
            source_account_id=account.id,
            destination_account_id=other_account.id,
            source_amount=Decimal("25.0000"),
            source_currency="USD",
            destination_amount=Decimal("25.0000"),
            destination_currency="USD",
            exchange_rate=Decimal("1.00000000"),
            transaction_date=date(2026, 1, 2),
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_monetary_precision_round_trip(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    expense_category: Category,
) -> None:
    precise_amount = Decimal("1234567890123.4567")
    tx = make_transaction(
        user=user,
        account=account,
        category=expense_category,
        amount=precise_amount,
    )
    db_session.add(tx)
    await db_session.flush()
    await db_session.refresh(tx)
    assert tx.amount == precise_amount
    assert isinstance(tx.amount, Decimal)


@pytest.mark.asyncio
async def test_transaction_relationships(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    expense_category: Category,
) -> None:
    tx = make_transaction(user=user, account=account, category=expense_category)
    db_session.add(tx)
    await db_session.flush()

    await db_session.refresh(user, attribute_names=["transactions"])
    await db_session.refresh(account, attribute_names=["transactions"])
    await db_session.refresh(expense_category, attribute_names=["transactions"])

    assert tx.user.id == user.id
    assert tx.account.id == account.id
    assert tx.category.id == expense_category.id
    assert tx in user.transactions
    assert tx in account.transactions
    assert tx in expense_category.transactions


@pytest.mark.asyncio
async def test_budget_category_association(
    db_session: AsyncSession,
    user: User,
    expense_category: Category,
) -> None:
    budget = Budget(
        user_id=user.id,
        name="Food",
        amount=Decimal("500.0000"),
        currency="USD",
        period=BudgetPeriod.MONTHLY,
        scope=BudgetScope.CATEGORY,
        start_date=date(2026, 1, 1),
    )
    budget.categories.append(expense_category)
    db_session.add(budget)
    await db_session.flush()

    result = await db_session.scalar(
        select(Budget).where(Budget.id == budget.id),
    )
    assert result is not None
    await db_session.refresh(result, attribute_names=["categories"])
    assert expense_category in result.categories


@pytest.mark.asyncio
async def test_recurring_transaction_scheduling_fields(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    expense_category: Category,
) -> None:
    recurring = RecurringTransaction(
        user_id=user.id,
        account_id=account.id,
        category_id=expense_category.id,
        transaction_type=TransactionType.EXPENSE,
        amount=Decimal("99.9900"),
        currency="USD",
        description="Rent",
        frequency=RecurringFrequency.MONTHLY,
        start_date=date(2026, 1, 1),
        next_execution_date=date(2026, 2, 1),
        is_active=True,
    )
    db_session.add(recurring)
    await db_session.flush()
    await db_session.refresh(recurring)
    assert recurring.next_execution_date == date(2026, 2, 1)
    assert recurring.frequency is RecurringFrequency.MONTHLY


@pytest.mark.asyncio
async def test_financial_goal_linked_account(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
) -> None:
    goal = FinancialGoal(
        user_id=user.id,
        name="Emergency fund",
        target_amount=Decimal("10000.0000"),
        current_amount=Decimal("2500.0000"),
        currency="USD",
        linked_account_id=account.id,
        status=GoalStatus.ACTIVE,
    )
    db_session.add(goal)
    await db_session.flush()
    await db_session.refresh(goal, attribute_names=["linked_account"])
    assert goal.linked_account is not None
    assert goal.linked_account.id == account.id


@pytest.mark.asyncio
async def test_audit_event_actor_relationship(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
) -> None:
    event = AuditEvent(
        actor_id=user.id,
        action=AuditAction.CREATED,
        entity_type="financial_account",
        entity_id=account.id,
        metadata_={"name": account.name},
    )
    db_session.add(event)
    await db_session.flush()
    await db_session.refresh(event, attribute_names=["actor"])
    assert event.actor.id == user.id


@pytest.mark.asyncio
async def test_notification_and_import_job_persist(
    db_session: AsyncSession,
    user: User,
) -> None:
    notification = Notification(
        user_id=user.id,
        notification_type=NotificationType.GENERAL,
        title="Hello",
        message="Test notification",
    )
    import_job = ImportJob(
        user_id=user.id,
        original_filename="transactions.csv",
        status=ImportJobStatus.PENDING,
    )
    db_session.add_all([notification, import_job])
    await db_session.flush()
    assert notification.id is not None
    assert import_job.id is not None


@pytest.mark.asyncio
async def test_deleting_user_with_accounts_is_restricted(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
) -> None:
    assert account.user_id == user.id
    await db_session.delete(user)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_transaction_soft_delete_column(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    expense_category: Category,
) -> None:
    tx = make_transaction(user=user, account=account, category=expense_category)
    db_session.add(tx)
    await db_session.flush()
    assert tx.deleted_at is None


@pytest.mark.asyncio
async def test_transaction_rejects_mismatched_account_owner(
    db_session: AsyncSession,
    user: User,
    other_user: User,
    expense_category: Category,
) -> None:
    other_account = FinancialAccount(
        user_id=other_user.id,
        name="Other Checking",
        account_type=AccountType.BANK,
        currency="USD",
    )
    db_session.add(other_account)
    await db_session.flush()

    db_session.add(
        Transaction(
            user_id=user.id,
            account_id=other_account.id,
            category_id=expense_category.id,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal("10.0000"),
            currency="USD",
            description="Cross-user account",
            transaction_date=date(2026, 1, 1),
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_same_currency_transfer_requires_equal_amounts(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    other_account: FinancialAccount,
) -> None:
    db_session.add(
        Transfer(
            user_id=user.id,
            source_account_id=account.id,
            destination_account_id=other_account.id,
            source_amount=Decimal("100.0000"),
            source_currency="USD",
            destination_amount=Decimal("99.9900"),
            destination_currency="USD",
            transaction_date=date(2026, 1, 3),
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_recurring_execution_is_unique_per_date(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    expense_category: Category,
) -> None:
    recurring = RecurringTransaction(
        user_id=user.id,
        account_id=account.id,
        category_id=expense_category.id,
        transaction_type=TransactionType.EXPENSE,
        amount=Decimal("50.0000"),
        currency="USD",
        description="Subscription",
        frequency=RecurringFrequency.MONTHLY,
        start_date=date(2026, 1, 1),
        next_execution_date=date(2026, 2, 1),
    )
    db_session.add(recurring)
    await db_session.flush()

    db_session.add(
        RecurringTransactionExecution(
            recurring_transaction_id=recurring.id,
            execution_date=date(2026, 2, 1),
        ),
    )
    await db_session.flush()
    db_session.add(
        RecurringTransactionExecution(
            recurring_transaction_id=recurring.id,
            execution_date=date(2026, 2, 1),
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_import_external_reference_unique_per_account(
    db_session: AsyncSession,
    user: User,
    account: FinancialAccount,
    expense_category: Category,
) -> None:
    first = make_transaction(
        user=user,
        account=account,
        category=expense_category,
        amount=Decimal("12.3400"),
    )
    first.external_reference = "bank-tx-001"
    db_session.add(first)
    await db_session.flush()

    duplicate = make_transaction(
        user=user,
        account=account,
        category=expense_category,
        amount=Decimal("12.3400"),
    )
    duplicate.external_reference = "bank-tx-001"
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_budget_rejects_invalid_date_range(
    db_session: AsyncSession,
    user: User,
) -> None:
    db_session.add(
        Budget(
            user_id=user.id,
            name="Invalid",
            amount=Decimal("100.0000"),
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            scope=BudgetScope.OVERALL,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 2, 1),
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_exchange_rate_pair_unique_per_date(db_session: AsyncSession) -> None:
    db_session.add(
        ExchangeRate(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal("0.92000000"),
            rate_date=date(2026, 1, 1),
            source="test",
        ),
    )
    await db_session.flush()
    db_session.add(
        ExchangeRate(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal("0.93000000"),
            rate_date=date(2026, 1, 1),
            source="test",
        ),
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_user_has_reporting_currency(
    db_session: AsyncSession,
    user: User,
) -> None:
    await db_session.refresh(user)
    assert user.reporting_currency == "USD"
