"""Business logic for session access control. Service owns transactions (commit)."""

import uuid
from typing import Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ExecutionStatus
from .repository import SessionAccessControlRepository
from .schema import (
    ApplicabilityEnum,
    DefinitionCreate,
    DefinitionResponse,
    DefinitionUpdate,
    ExecutionCreate,
    ExecutionResponse,
    ExecutionStatusEnum,
    ExecutionUpdate,
    PaginatedResponse,
    RequirementSpec,
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
_SUPPORTED_EXECUTION_FILTERS = {"definition_id", "status", "session_state"}


def _build_default_requirements() -> list[dict]:
    """Return the default FR-1..FR-30 requirement specs for session access control."""
    specs = [
        # Page Access (FR-1..FR-6)
        RequirementSpec(
            fr_id="FR-1",
            description="Page loads without errors for guest (unauthenticated) session",
            lifecycle_section="page_access",
            acceptance_signal="HTTP 200; no JS console errors; DOM ready for guest user",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-2",
            description="Page loads and renders correctly for authenticated session",
            lifecycle_section="page_access",
            acceptance_signal="HTTP 200; authenticated content visible; no errors",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-3",
            description="Expired session is detected and handled on page access",
            lifecycle_section="page_access",
            acceptance_signal="Expired session results in redirect or expiry message",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-4",
            description="Unauthenticated access to protected page redirects to login",
            lifecycle_section="page_access",
            acceptance_signal="Guest accessing protected route is redirected to login URL",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-5",
            description="Page identity indicator is present and correct",
            lifecycle_section="page_access",
            acceptance_signal="Title, heading, or landmark matches expected page identity",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-6",
            description="Viewport renders correctly at specified width/height for all session states",
            lifecycle_section="page_access",
            acceptance_signal="No horizontal scroll; elements within viewport bounds",
            applicability=ApplicabilityEnum.applicable,
        ),
        # Session Initialization (FR-7..FR-12)
        RequirementSpec(
            fr_id="FR-7",
            description="Session token is set in storage after successful authentication",
            lifecycle_section="session_initialization",
            acceptance_signal="Auth token present in localStorage/sessionStorage/cookie after login",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-8",
            description="Session persists across page refresh for authenticated user",
            lifecycle_section="session_initialization",
            acceptance_signal="Authenticated state maintained after browser refresh",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-9",
            description="Clean session is established before test when required",
            lifecycle_section="session_initialization",
            acceptance_signal="Previous session data cleared; fresh session context active",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-10",
            description="Session state is correctly reflected in UI indicators",
            lifecycle_section="session_initialization",
            acceptance_signal="User avatar, name, or auth indicator matches session state",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-11",
            description="Logout clears session and redirects to guest state",
            lifecycle_section="session_initialization",
            acceptance_signal="Session token removed; user redirected to public/login page",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-12",
            description="Session context is available to child components after initialization",
            lifecycle_section="session_initialization",
            acceptance_signal="Session-dependent UI elements render correctly without re-fetch",
            applicability=ApplicabilityEnum.optional,
        ),
        # Guarded Actions (FR-13..FR-18)
        RequirementSpec(
            fr_id="FR-13",
            description="Guarded action is blocked for guest (unauthenticated) user",
            lifecycle_section="guarded_actions",
            acceptance_signal="Action button disabled or auth prompt shown for guest",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-14",
            description="Guarded action succeeds for authenticated user",
            lifecycle_section="guarded_actions",
            acceptance_signal="Action completes successfully; success feedback shown",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-15",
            description="Guarded action is blocked for expired session",
            lifecycle_section="guarded_actions",
            acceptance_signal="Expired session triggers re-auth prompt or error on action attempt",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-16",
            description="Feedback is shown when guarded action is blocked",
            lifecycle_section="guarded_actions",
            acceptance_signal="Visible message or prompt explains why action is unavailable",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-17",
            description="Blocked action prompt provides path to authenticate",
            lifecycle_section="guarded_actions",
            acceptance_signal="Login link or auth modal available from blocked action feedback",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-18",
            description="Guarded action state updates correctly after session change",
            lifecycle_section="guarded_actions",
            acceptance_signal="Action availability updates without page reload after auth change",
            applicability=ApplicabilityEnum.applicable,
        ),
        # Protected Navigation (FR-19..FR-24)
        RequirementSpec(
            fr_id="FR-19",
            description="Direct URL access to protected route by guest triggers redirect",
            lifecycle_section="protected_navigation",
            acceptance_signal="Guest navigating directly to /protected is redirected to login",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-20",
            description="Authenticated user can access all permitted routes directly",
            lifecycle_section="protected_navigation",
            acceptance_signal="All auth-required routes load without redirect for active session",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-21",
            description="Expired session on protected route redirects to re-authentication",
            lifecycle_section="protected_navigation",
            acceptance_signal="Expired session navigating to protected route prompts re-auth",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-22",
            description="Post-login redirect returns user to originally requested URL",
            lifecycle_section="protected_navigation",
            acceptance_signal="After login, user lands on the originally requested protected URL",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-23",
            description="Back navigation from protected page respects session state",
            lifecycle_section="protected_navigation",
            acceptance_signal="Browser back button preserves session context on previous page",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-24",
            description="Blocked session state prevents access to all protected routes",
            lifecycle_section="protected_navigation",
            acceptance_signal="Blocked session results in access denied for all protected paths",
            applicability=ApplicabilityEnum.applicable,
        ),
        # Session Expiry (FR-25..FR-28)
        RequirementSpec(
            fr_id="FR-25",
            description="Session expiry is detected proactively before action attempt",
            lifecycle_section="session_expiry",
            acceptance_signal="Expiry detected via token check before user action is triggered",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-26",
            description="Expired session message is visible and informative",
            lifecycle_section="session_expiry",
            acceptance_signal="Expiry message text is visible and explains the session state",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-27",
            description="Re-authentication flow is accessible from expired session state",
            lifecycle_section="session_expiry",
            acceptance_signal="Login link or re-auth button present and functional on expiry",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-28",
            description="Re-authentication restores full access after session expiry",
            lifecycle_section="session_expiry",
            acceptance_signal="New session after re-auth grants access to all permitted routes",
            applicability=ApplicabilityEnum.required,
        ),
        # Loading, Empty, and Error States (FR-29..FR-30)
        RequirementSpec(
            fr_id="FR-29",
            description="Loading state is shown during session validation and page initialization",
            lifecycle_section="loading_empty_error",
            acceptance_signal="Loading indicator visible during session check; hides on completion",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-30",
            description="Error state is handled gracefully with recovery option available",
            lifecycle_section="loading_empty_error",
            acceptance_signal="Session/network error shows error message with retry or re-auth path",
            applicability=ApplicabilityEnum.applicable,
        ),
    ]
    return [s.model_dump() for s in specs]


class SessionAccessControlService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SessionAccessControlRepository(db)

    # ─── Definitions ─────────────────────────────────────────────────────────

    async def create_definition(self, data: DefinitionCreate) -> DefinitionResponse:
        payload = data.model_dump()
        if not payload.get("requirements"):
            payload["requirements"] = _build_default_requirements()
        obj = await self.repo.create_definition(payload)
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("session_access_control.definition.created", id=str(obj.id), name=obj.name)
        return DefinitionResponse.model_validate(obj)

    async def get_definition(self, definition_id: uuid.UUID) -> DefinitionResponse:
        obj = await self.repo.get_definition(definition_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Definition not found")
        return DefinitionResponse.model_validate(obj)

    async def list_definitions(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> PaginatedResponse[DefinitionResponse]:
        if filters:
            unsupported = set(filters.keys()) - _SUPPORTED_DEFINITION_FILTERS
            if unsupported:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported filter keys: {sorted(unsupported)}",
                )
        items, total = await self.repo.list_definitions(page, page_size, sort_by, sort_dir, filters)
        return PaginatedResponse(
            items=[DefinitionResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_definition(
        self, definition_id: uuid.UUID, data: DefinitionUpdate
    ) -> DefinitionResponse:
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        obj = await self.repo.update_definition(definition_id, payload)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Definition not found")
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("session_access_control.definition.updated", id=str(obj.id))
        return DefinitionResponse.model_validate(obj)

    async def delete_definition(self, definition_id: uuid.UUID) -> None:
        deleted = await self.repo.delete_definition(definition_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Definition not found")
        await self.db.commit()
        logger.info("session_access_control.definition.deleted", id=str(definition_id))

    # ─── Executions ──────────────────────────────────────────────────────────

    async def create_execution(self, data: ExecutionCreate) -> ExecutionResponse:
        defn = await self.repo.get_definition(data.definition_id)
        if defn is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced definition not found",
            )
        payload = data.model_dump()
        payload["status"] = payload["status"].value
        if payload.get("session_state") is not None:
            payload["session_state"] = payload["session_state"].value
        obj = await self.repo.create_execution(payload)
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("session_access_control.execution.created", id=str(obj.id))
        return ExecutionResponse.model_validate(obj)

    async def get_execution(self, execution_id: uuid.UUID) -> ExecutionResponse:
        obj = await self.repo.get_execution(execution_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
        return ExecutionResponse.model_validate(obj)

    async def list_executions(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> PaginatedResponse[ExecutionResponse]:
        if filters:
            unsupported = set(filters.keys()) - _SUPPORTED_EXECUTION_FILTERS
            if unsupported:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported filter keys: {sorted(unsupported)}",
                )
        items, total = await self.repo.list_executions(page, page_size, sort_by, sort_dir, filters)
        return PaginatedResponse(
            items=[ExecutionResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_execution(
        self, execution_id: uuid.UUID, data: ExecutionUpdate
    ) -> ExecutionResponse:
        obj = await self.repo.get_execution(execution_id)
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
        if "session_state" in payload and payload["session_state"] is not None:
            from .schema import SessionStateEnum
            if isinstance(payload["session_state"], SessionStateEnum):
                payload["session_state"] = payload["session_state"].value

        updated = await self.repo.update_execution(execution_id, payload)
        await self.db.commit()
        await self.db.refresh(updated)
        logger.info("session_access_control.execution.updated", id=str(execution_id))
        return ExecutionResponse.model_validate(updated)
