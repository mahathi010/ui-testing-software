"""FastAPI router for error response handling — /v1/error-response."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from .schema import (
    ErrorResponseDefinitionCreate,
    ErrorResponseDefinitionResponse,
    ErrorResponseDefinitionUpdate,
    ErrorResponseExecutionCreate,
    ErrorResponseExecutionResponse,
    ErrorResponseExecutionUpdate,
    PaginatedResponse,
)
from .service import ErrorResponseDefinitionService, ErrorResponseExecutionService

router = APIRouter(
    prefix="/v1/error-response",
    tags=["error-response"],
)


# ─── Definitions ─────────────────────────────────────────────────────────────


@router.post(
    "/definitions",
    response_model=ErrorResponseDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an error-response definition",
)
async def create_definition(
    body: ErrorResponseDefinitionCreate,
    db: AsyncSession = Depends(get_db),
) -> ErrorResponseDefinitionResponse:
    svc = ErrorResponseDefinitionService(db)
    return await svc.create_definition(body)


@router.get(
    "/definitions",
    response_model=PaginatedResponse[ErrorResponseDefinitionResponse],
    status_code=status.HTTP_200_OK,
    summary="List error-response definitions",
)
async def list_definitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    is_active: Optional[bool] = Query(None),
    name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ErrorResponseDefinitionResponse]:
    filters: dict = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if name is not None:
        filters["name"] = name
    svc = ErrorResponseDefinitionService(db)
    return await svc.list_definitions(page, page_size, sort_by, sort_dir, filters or None)


@router.get(
    "/definitions/{definition_id}",
    response_model=ErrorResponseDefinitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single error-response definition",
)
async def get_definition(
    definition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ErrorResponseDefinitionResponse:
    svc = ErrorResponseDefinitionService(db)
    return await svc.get_definition(definition_id)


@router.put(
    "/definitions/{definition_id}",
    response_model=ErrorResponseDefinitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an error-response definition",
)
async def update_definition(
    definition_id: uuid.UUID,
    body: ErrorResponseDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
) -> ErrorResponseDefinitionResponse:
    svc = ErrorResponseDefinitionService(db)
    return await svc.update_definition(definition_id, body)


@router.delete(
    "/definitions/{definition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an error-response definition",
)
async def delete_definition(
    definition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = ErrorResponseDefinitionService(db)
    await svc.delete_definition(definition_id)


# ─── Executions ──────────────────────────────────────────────────────────────


@router.post(
    "/executions",
    response_model=ErrorResponseExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an error-response execution record",
)
async def create_execution(
    body: ErrorResponseExecutionCreate,
    db: AsyncSession = Depends(get_db),
) -> ErrorResponseExecutionResponse:
    svc = ErrorResponseExecutionService(db)
    return await svc.create_execution(body)


@router.get(
    "/executions",
    response_model=PaginatedResponse[ErrorResponseExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="List error-response executions",
)
async def list_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    definition_id: Optional[uuid.UUID] = Query(None),
    filter_status: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ErrorResponseExecutionResponse]:
    filters: dict = {}
    if definition_id is not None:
        filters["definition_id"] = definition_id
    if filter_status is not None:
        filters["status"] = filter_status
    svc = ErrorResponseExecutionService(db)
    return await svc.list_executions(page, page_size, sort_by, sort_dir, filters or None)


@router.get(
    "/executions/{execution_id}",
    response_model=ErrorResponseExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single error-response execution",
)
async def get_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ErrorResponseExecutionResponse:
    svc = ErrorResponseExecutionService(db)
    return await svc.get_execution(execution_id)


@router.put(
    "/executions/{execution_id}",
    response_model=ErrorResponseExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an error-response execution",
)
async def update_execution(
    execution_id: uuid.UUID,
    body: ErrorResponseExecutionUpdate,
    db: AsyncSession = Depends(get_db),
) -> ErrorResponseExecutionResponse:
    svc = ErrorResponseExecutionService(db)
    return await svc.update_execution(execution_id, body)
