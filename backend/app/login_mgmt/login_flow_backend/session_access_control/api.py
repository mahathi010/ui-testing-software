"""FastAPI router for session access control — /v1/session-access."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from .schema import (
    AccessRecordCreate,
    AccessRecordResponse,
    GuardedActionRequest,
    GuardedActionResponse,
    PaginatedResponse,
    ResourceCreate,
    ResourceResponse,
    ResourceUpdate,
    SessionCheckRequest,
    SessionCheckResponse,
)
from .service import SessionAccessControlService

router = APIRouter(
    prefix="/v1/session-access",
    tags=["session-access"],
)


# ─── Session Check / Guard ────────────────────────────────────────────────────


@router.post(
    "/check",
    response_model=SessionCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check session access for a resource",
)
async def check_session_access(
    body: SessionCheckRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionCheckResponse:
    svc = SessionAccessControlService(db)
    return await svc.check_session_access(body)


@router.post(
    "/guard",
    response_model=GuardedActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Attempt a guarded action",
)
async def attempt_guarded_action(
    body: GuardedActionRequest,
    db: AsyncSession = Depends(get_db),
) -> GuardedActionResponse:
    svc = SessionAccessControlService(db)
    return await svc.attempt_guarded_action(body)


# ─── Resources ────────────────────────────────────────────────────────────────


@router.post(
    "/resources",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a protected resource",
)
async def create_resource(
    body: ResourceCreate,
    db: AsyncSession = Depends(get_db),
) -> ResourceResponse:
    svc = SessionAccessControlService(db)
    return await svc.create_resource(body)


@router.get(
    "/resources",
    response_model=PaginatedResponse[ResourceResponse],
    status_code=status.HTTP_200_OK,
    summary="List protected resources",
)
async def list_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    is_active: Optional[bool] = Query(None),
    protection_level: Optional[str] = Query(None),
    resource_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ResourceResponse]:
    filters: dict = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if protection_level is not None:
        filters["protection_level"] = protection_level
    if resource_name is not None:
        filters["resource_name"] = resource_name
    svc = SessionAccessControlService(db)
    return await svc.list_resources(page, page_size, sort_by, sort_dir, filters or None)


@router.get(
    "/resources/{resource_id}",
    response_model=ResourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a protected resource",
)
async def get_resource(
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ResourceResponse:
    svc = SessionAccessControlService(db)
    return await svc.get_resource(resource_id)


@router.put(
    "/resources/{resource_id}",
    response_model=ResourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a protected resource",
)
async def update_resource(
    resource_id: uuid.UUID,
    body: ResourceUpdate,
    db: AsyncSession = Depends(get_db),
) -> ResourceResponse:
    svc = SessionAccessControlService(db)
    return await svc.update_resource(resource_id, body)


@router.delete(
    "/resources/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a protected resource",
)
async def delete_resource(
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = SessionAccessControlService(db)
    await svc.delete_resource(resource_id)


# ─── Records ──────────────────────────────────────────────────────────────────


@router.get(
    "/records",
    response_model=PaginatedResponse[AccessRecordResponse],
    status_code=status.HTTP_200_OK,
    summary="List session access records",
)
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    resource_id: Optional[uuid.UUID] = Query(None),
    filter_session_status: Optional[str] = Query(None, alias="session_status"),
    filter_outcome: Optional[str] = Query(None, alias="outcome"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AccessRecordResponse]:
    filters: dict = {}
    if resource_id is not None:
        filters["resource_id"] = resource_id
    if filter_session_status is not None:
        filters["session_status"] = filter_session_status
    if filter_outcome is not None:
        filters["outcome"] = filter_outcome
    svc = SessionAccessControlService(db)
    return await svc.list_records(page, page_size, sort_by, sort_dir, filters or None)


@router.post(
    "/records",
    response_model=AccessRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create an access record",
)
async def create_record(
    body: AccessRecordCreate,
    db: AsyncSession = Depends(get_db),
) -> AccessRecordResponse:
    svc = SessionAccessControlService(db)
    return await svc.create_record(body)
