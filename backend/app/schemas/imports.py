"""CSV import API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import ImportJobStatus


class ImportRowErrorResponse(BaseModel):
    row_number: int
    code: str
    message: str
    raw: dict[str, str] = Field(default_factory=dict)


class ImportPreviewRowResponse(BaseModel):
    row_number: int
    transaction_date: str
    transaction_type: str
    amount: str
    description: str
    category: str
    category_id: str | None = None
    external_reference: str | None = None
    notes: str | None = None
    is_duplicate: bool = False
    duplicate_reason: str | None = None


class ImportJobStats(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    imported_rows: int
    skipped_rows: int
    duplicate_rows: int


class ImportJobResponse(BaseModel):
    id: str
    target_account_id: str | None
    original_filename: str
    content_type: str | None
    status: ImportJobStatus
    stats: ImportJobStats
    preview_rows: list[ImportPreviewRowResponse] = Field(default_factory=list)
    errors: list[ImportRowErrorResponse] = Field(default_factory=list)
    completed_at: str | None = None
    created_at: str
    updated_at: str


class ImportConfirmRequest(BaseModel):
    skip_duplicates: bool = True
