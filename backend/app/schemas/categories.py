"""Category API schemas."""

from pydantic import BaseModel, Field

from app.models.enums import CategoryStatus, CategoryType


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category_type: CategoryType
    icon: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=32)


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    icon: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=32)


class CategoryResponse(BaseModel):
    id: str
    name: str
    category_type: CategoryType
    icon: str | None
    color: str | None
    is_system: bool
    status: CategoryStatus
    archived_at: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
