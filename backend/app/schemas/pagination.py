"""Pagination request and response schemas."""

from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    items: list[T]
    page: int
    page_size: int
    total_items: int
    total_pages: int


def pagination_params(
    *,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100,
) -> tuple[int, int]:
    """Return validated offset and limit for SQL queries."""
    safe_page = max(page, 1)
    safe_size = min(max(page_size, 1), max_page_size)
    offset = (safe_page - 1) * safe_size
    return offset, safe_size


def build_paginated_response[T](
    *,
    items: list[T],
    page: int,
    page_size: int,
    total_items: int,
) -> PaginatedResponse[T]:
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    return PaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages if total_items else 0,
    )
