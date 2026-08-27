"""CSV import endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.schemas.imports import ImportConfirmRequest, ImportJobResponse
from app.schemas.pagination import PaginatedResponse
from app.services import import_service

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", response_model=ImportJobResponse, status_code=status.HTTP_201_CREATED)
async def upload_import(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    account_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
) -> ImportJobResponse:
    raw = await import_service.read_upload_limited(
        file,
        max_bytes=settings.import_max_file_bytes,
    )
    return await import_service.upload_and_preview(
        session,
        user_id=current_user.id,
        settings=settings,
        account_id=account_id,
        filename=file.filename,
        content_type=file.content_type,
        raw_bytes=raw,
    )


@router.get("", response_model=PaginatedResponse[ImportJobResponse])
async def list_imports(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
) -> PaginatedResponse[ImportJobResponse]:
    return await import_service.list_import_jobs(
        session,
        user_id=current_user.id,
        settings=settings,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=ImportJobResponse)
async def get_import(
    job_id: UUID,
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
) -> ImportJobResponse:
    return await import_service.get_import_job(
        session,
        user_id=current_user.id,
        settings=settings,
        job_id=job_id,
    )


@router.post("/{job_id}/confirm", response_model=ImportJobResponse)
async def confirm_import(
    job_id: UUID,
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    payload: ImportConfirmRequest | None = None,
) -> ImportJobResponse:
    request = payload or ImportConfirmRequest()
    return await import_service.confirm_import(
        session,
        user_id=current_user.id,
        settings=settings,
        job_id=job_id,
        skip_duplicates=request.skip_duplicates,
    )
