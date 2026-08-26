"""Domain enumerations persisted in PostgreSQL."""

from enum import StrEnum


class AccountType(StrEnum):
    CASH = "cash"
    BANK = "bank"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    DIGITAL_WALLET = "digital_wallet"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CategoryType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    UNIVERSAL = "universal"


class CategoryStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class TransactionType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class RecurringFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class BudgetPeriod(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class BudgetScope(StrEnum):
    CATEGORY = "category"
    OVERALL = "overall"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ImportJobStatus(StrEnum):
    PENDING = "pending"
    PREVIEW = "preview"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationType(StrEnum):
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    RECURRING_CREATED = "recurring_created"
    GOAL_MILESTONE = "goal_milestone"
    IMPORT_COMPLETED = "import_completed"
    IMPORT_FAILED = "import_failed"
    GENERAL = "general"


class AuditAction(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ARCHIVED = "archived"
    IMPORT_EXECUTED = "import_executed"
