"""FastAPI router for credential validation — /v1/credential-validation."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from .schema import (
    DefinitionCreate,
    DefinitionResponse,
    DefinitionUpdate,
    ExecutionCreate,
    ExecutionResponse,
    ExecutionUpdate,
    PaginatedResponse,
)
from .service import CredentialValidationService

router = APIRouter(
    prefix="/v1/credential-validation",
    tags=["credential-validation"],
)

_ALLOWED_DEFINITION_FILTER_KEYS = {"is_active", "name"}
_ALLOWED_EXECUTION_FILTER_KEYS = {"definition_id", "status"}


# ─── Definitions ─────────────────────────────────────────────────────────────


@router.post(
    "/definitions",
    response_model=DefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a credential-validation definition",
)
async def create_definition(
    body: DefinitionCreate,
    db: AsyncSession = Depends(get_db),
) -> DefinitionResponse:
    svc = CredentialValidationService(db)
    return await svc.create_definition(body)


@router.get(
    "/definitions",
    response_model=PaginatedResponse[DefinitionResponse],
    status_code=status.HTTP_200_OK,
    summary="List credential-validation definitions",
)
async def list_definitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    is_active: Optional[bool] = Query(None),
    name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DefinitionResponse]:
    filters: dict = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if name is not None:
        filters["name"] = name
    svc = CredentialValidationService(db)
    return await svc.list_definitions(page, page_size, sort_by, sort_dir, filters or None)


@router.get(
    "/definitions/{definition_id}",
    response_model=DefinitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single credential-validation definition",
)
async def get_definition(
    definition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DefinitionResponse:
    svc = CredentialValidationService(db)
    return await svc.get_definition(definition_id)


@router.put(
    "/definitions/{definition_id}",
    response_model=DefinitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a credential-validation definition",
)
async def update_definition(
    definition_id: uuid.UUID,
    body: DefinitionUpdate,
    db: AsyncSession = Depends(get_db),
) -> DefinitionResponse:
    svc = CredentialValidationService(db)
    return await svc.update_definition(definition_id, body)


@router.delete(
    "/definitions/{definition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a credential-validation definition",
)
async def delete_definition(
    definition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = CredentialValidationService(db)
    await svc.delete_definition(definition_id)


# ─── Executions ──────────────────────────────────────────────────────────────


@router.post(
    "/executions",
    response_model=ExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a credential-validation execution record",
)
async def create_execution(
    body: ExecutionCreate,
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    svc = CredentialValidationService(db)
    return await svc.create_execution(body)


@router.get(
    "/executions",
    response_model=PaginatedResponse[ExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="List credential-validation executions",
)
async def list_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    definition_id: Optional[uuid.UUID] = Query(None),
    filter_status: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ExecutionResponse]:
    filters: dict = {}
    if definition_id is not None:
        filters["definition_id"] = definition_id
    if filter_status is not None:
        filters["status"] = filter_status
    svc = CredentialValidationService(db)
    return await svc.list_executions(page, page_size, sort_by, sort_dir, filters or None)


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single credential-validation execution",
)
async def get_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    svc = CredentialValidationService(db)
    return await svc.get_execution(execution_id)


@router.put(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a credential-validation execution",
)
async def update_execution(
    execution_id: uuid.UUID,
    body: ExecutionUpdate,
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    svc = CredentialValidationService(db)
    return await svc.update_execution(execution_id, body)
