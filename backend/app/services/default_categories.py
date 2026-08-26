"""Default category seed data for new users."""

import uuid

from app.models.category import Category
from app.models.enums import CategoryType

DEFAULT_EXPENSE_CATEGORIES: tuple[str, ...] = (
    "Housing",
    "Food",
    "Groceries",
    "Restaurants",
    "Transport",
    "Shopping",
    "Entertainment",
    "Health",
    "Education",
    "Travel",
    "Utilities",
    "Subscriptions",
    "Personal",
    "Other",
)

DEFAULT_INCOME_CATEGORIES: tuple[str, ...] = (
    "Salary",
    "Freelance",
    "Bonus",
    "Investment",
    "Gift",
    "Other",
)


def build_default_categories(user_id: uuid.UUID) -> list[Category]:
    """Build user-owned default categories for registration."""
    categories: list[Category] = []
    for name in DEFAULT_EXPENSE_CATEGORIES:
        categories.append(
            Category(
                user_id=user_id,
                name=name,
                category_type=CategoryType.EXPENSE,
                is_system=False,
            ),
        )
    for name in DEFAULT_INCOME_CATEGORIES:
        categories.append(
            Category(
                user_id=user_id,
                name=name,
                category_type=CategoryType.INCOME,
                is_system=False,
            ),
        )
    return categories
