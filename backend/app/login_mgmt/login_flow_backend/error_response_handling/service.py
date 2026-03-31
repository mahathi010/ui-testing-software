"""Business logic for error response handling. Service owns transactions (commit)."""

import uuid
from typing import Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ExecutionStatus
from .repository import ErrorResponseDefinitionRepository, ErrorResponseExecutionRepository
from .schema import (
    ErrorResponseDefinitionCreate,
    ErrorResponseDefinitionResponse,
    ErrorResponseDefinitionUpdate,
    ErrorResponseExecutionCreate,
    ErrorResponseExecutionResponse,
    ErrorResponseExecutionUpdate,
    ExecutionStatusEnum,
    PaginatedResponse,
)

logger = structlog.get_logger(__name__)

_VALID_EXECUTION_TRANSITIONS: dict[ExecutionStatusEnum, set[ExecutionStatusEnum]] = {
    ExecutionStatusEnum.pending: {ExecutionStatusEnum.running, ExecutionStatusEnum.skipped},
    ExecutionStatusEnum.running: {ExecutionStatusEnum.passed, ExecutionStatusEnum.failed, ExecutionStatusEnum.error},
    ExecutionStatusEnum.passed: set(),
    ExecutionStatusEnum.failed: {ExecutionStatusEnum.pending},
    ExecutionStatusEnum.error: {ExecutionStatusEnum.pending},
    ExecutionStatusEnum.skipped: {ExecutionStatusEnum.pending},
}

_SUPPORTED_DEFINITION_FILTERS = {"is_active", "name"}
_SUPPORTED_EXECUTION_FILTERS = {"definition_id", "status"}


def _build_default_requirements() -> list[dict]:
    """Return the default FR-1..FR-24 requirement specs for error response handling."""
    return [
        # Initial Load & Access (FR-1..FR-6)
        {"fr_id": "FR-1", "description": "Page loads without errors and becomes reachable", "lifecycle_section": "initial_load", "acceptance_signal": "HTTP 200; no JS console errors; DOM ready", "applicability": "required"},
        {"fr_id": "FR-2", "description": "No browser console errors on initial load", "lifecycle_section": "initial_load", "acceptance_signal": "console.error not called on load", "applicability": "required"},
        {"fr_id": "FR-3", "description": "Main container element is present in the viewport", "lifecycle_section": "initial_load", "acceptance_signal": "main-container element is visible", "applicability": "required"},
        {"fr_id": "FR-4", "description": "Identifying title or heading text is present", "lifecycle_section": "initial_load", "acceptance_signal": "h1 or title element has non-empty text", "applicability": "required"},
        {"fr_id": "FR-5", "description": "Page refreshes correctly and container remains visible", "lifecycle_section": "initial_load", "acceptance_signal": "After reload(), main container still visible", "applicability": "required"},
        {"fr_id": "FR-6", "description": "First visit shows expected default state", "lifecycle_section": "initial_load", "acceptance_signal": "No pre-selected or persisted state on first visit", "applicability": "applicable"},
        # Page Structure & Content (FR-7..FR-12)
        {"fr_id": "FR-7", "description": "Content is grouped into logical sections", "lifecycle_section": "page_structure", "acceptance_signal": "Multiple section or region elements present", "applicability": "required"},
        {"fr_id": "FR-8", "description": "Each section has a heading element", "lifecycle_section": "page_structure", "acceptance_signal": "Heading element within each section", "applicability": "required"},
        {"fr_id": "FR-9", "description": "Content text is readable and not hidden", "lifecycle_section": "page_structure", "acceptance_signal": "Text content has non-zero length and is visible", "applicability": "required"},
        {"fr_id": "FR-10", "description": "List items render correctly when items are present", "lifecycle_section": "page_structure", "acceptance_signal": "Count of rendered items matches mock item count", "applicability": "required"},
        {"fr_id": "FR-11", "description": "Actionable controls are enabled and interactive", "lifecycle_section": "page_structure", "acceptance_signal": "Buttons and links are not disabled", "applicability": "required"},
        {"fr_id": "FR-12", "description": "Items are not rendered more than once", "lifecycle_section": "page_structure", "acceptance_signal": "Rendered item count equals mock item count", "applicability": "required"},
        # Interactions & Navigation (FR-13..FR-18)
        {"fr_id": "FR-13", "description": "Primary CTA click triggers expected behavior", "lifecycle_section": "interactions", "acceptance_signal": "CTA click navigates or triggers action", "applicability": "required"},
        {"fr_id": "FR-14", "description": "Links have valid href destinations", "lifecycle_section": "interactions", "acceptance_signal": "Links have non-empty href attributes", "applicability": "required"},
        {"fr_id": "FR-15", "description": "Clicking content item navigates to detail view", "lifecycle_section": "interactions", "acceptance_signal": "URL or content changes after item click", "applicability": "applicable"},
        {"fr_id": "FR-16", "description": "Hover, focus, and active states function correctly", "lifecycle_section": "interactions", "acceptance_signal": "Focus on control applies visible state", "applicability": "applicable"},
        {"fr_id": "FR-17", "description": "Back navigation returns user to previous location", "lifecycle_section": "interactions", "acceptance_signal": "go_back() lands on origin URL", "applicability": "applicable"},
        {"fr_id": "FR-18", "description": "Clicking non-interactive elements does not cause errors", "lifecycle_section": "interactions", "acceptance_signal": "Non-actionable click does not throw", "applicability": "applicable"},
        # Content States & Error Handling (FR-19..FR-24)
        {"fr_id": "FR-19", "description": "Loading indicator shows during async transitions", "lifecycle_section": "error_handling", "acceptance_signal": "Loading state visible before content appears", "applicability": "required"},
        {"fr_id": "FR-20", "description": "Empty state message shown when no items returned", "lifecycle_section": "error_handling", "acceptance_signal": "Empty state element visible with zero-item response", "applicability": "required"},
        {"fr_id": "FR-21", "description": "Failed API response shows error or fallback UI", "lifecycle_section": "error_handling", "acceptance_signal": "Error message or fallback visible on 500 response", "applicability": "required"},
        {"fr_id": "FR-22", "description": "Malformed content is contained and does not crash the page", "lifecycle_section": "error_handling", "acceptance_signal": "Page remains functional with invalid payload", "applicability": "required"},
        {"fr_id": "FR-23", "description": "CTA and actions are blocked or disabled during error state", "lifecycle_section": "error_handling", "acceptance_signal": "CTA disabled or absent after 500 response", "applicability": "applicable"},
        {"fr_id": "FR-24", "description": "Content loads correctly after transient error and retry", "lifecycle_section": "error_handling", "acceptance_signal": "After 500 then 200, content renders correctly", "applicability": "required"},
    ]


class ErrorResponseDefinitionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ErrorResponseDefinitionRepository(db)

    async def create_definition(
        self, data: ErrorResponseDefinitionCreate
    ) -> ErrorResponseDefinitionResponse:
        payload = data.model_dump()
        if not payload.get("requirements"):
            payload["requirements"] = _build_default_requirements()
        obj = await self.repo.create(payload)
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("error_response.definition.created", id=str(obj.id), name=obj.name)
        return ErrorResponseDefinitionResponse.model_validate(obj)

    async def get_definition(self, definition_id: uuid.UUID) -> ErrorResponseDefinitionResponse:
        obj = await self.repo.find_by_id(definition_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Definition not found")
        return ErrorResponseDefinitionResponse.model_validate(obj)

    async def list_definitions(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> PaginatedResponse[ErrorResponseDefinitionResponse]:
        if filters:
            unsupported = set(filters.keys()) - _SUPPORTED_DEFINITION_FILTERS
            if unsupported:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported filter keys: {sorted(unsupported)}",
                )
        items, total = await self.repo.find_all(page, page_size, sort_by, sort_dir, filters)
        return PaginatedResponse(
            items=[ErrorResponseDefinitionResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_definition(
        self, definition_id: uuid.UUID, data: ErrorResponseDefinitionUpdate
    ) -> ErrorResponseDefinitionResponse:
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        obj = await self.repo.update(definition_id, payload)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Definition not found")
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("error_response.definition.updated", id=str(obj.id))
        return ErrorResponseDefinitionResponse.model_validate(obj)

    async def delete_definition(self, definition_id: uuid.UUID) -> None:
        deleted = await self.repo.delete(definition_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Definition not found")
        await self.db.commit()
        logger.info("error_response.definition.deleted", id=str(definition_id))


class ErrorResponseExecutionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ErrorResponseExecutionRepository(db)
        self.definition_repo = ErrorResponseDefinitionRepository(db)

    async def create_execution(
        self, data: ErrorResponseExecutionCreate
    ) -> ErrorResponseExecutionResponse:
        defn = await self.definition_repo.find_by_id(data.definition_id)
        if defn is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced definition not found",
            )
        payload = data.model_dump()
        payload["status"] = payload["status"].value
        obj = await self.repo.create(payload)
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("error_response.execution.created", id=str(obj.id))
        return ErrorResponseExecutionResponse.model_validate(obj)

    async def get_execution(self, execution_id: uuid.UUID) -> ErrorResponseExecutionResponse:
        obj = await self.repo.find_by_id(execution_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
        return ErrorResponseExecutionResponse.model_validate(obj)

    async def list_executions(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> PaginatedResponse[ErrorResponseExecutionResponse]:
        if filters:
            unsupported = set(filters.keys()) - _SUPPORTED_EXECUTION_FILTERS
            if unsupported:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported filter keys: {sorted(unsupported)}",
                )
        items, total = await self.repo.find_all(page, page_size, sort_by, sort_dir, filters)
        return PaginatedResponse(
            items=[ErrorResponseExecutionResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_execution(
        self, execution_id: uuid.UUID, data: ErrorResponseExecutionUpdate
    ) -> ErrorResponseExecutionResponse:
        obj = await self.repo.find_by_id(execution_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

        if data.status is not None:
            current = ExecutionStatusEnum(obj.status.value if hasattr(obj.status, "value") else obj.status)
            allowed = _VALID_EXECUTION_TRANSITIONS.get(current, set())
            if data.status not in allowed and data.status != current:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid status transition: {current} → {data.status}",
                )

        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        if "status" in payload and isinstance(payload["status"], ExecutionStatusEnum):
            payload["status"] = payload["status"].value

        updated = await self.repo.update(execution_id, payload)
        await self.db.commit()
        await self.db.refresh(updated)
        logger.info("error_response.execution.updated", id=str(execution_id))
        return ErrorResponseExecutionResponse.model_validate(updated)
