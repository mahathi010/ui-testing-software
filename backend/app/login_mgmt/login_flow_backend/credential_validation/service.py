"""Business logic for credential validation. Service owns transactions (commit)."""

import uuid
from typing import Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ExecutionStatus
from .repository import CredentialValidationRepository
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
_SUPPORTED_EXECUTION_FILTERS = {"definition_id", "status"}


def _build_default_requirements() -> list[dict]:
    """Return the default FR-1..FR-32 requirement specs."""
    specs = [
        # Initial Rendering (FR-1..FR-6)
        RequirementSpec(
            fr_id="FR-1",
            description="Page loads without errors and becomes interactive",
            lifecycle_section="initial_rendering",
            acceptance_signal="HTTP 200; no JS console errors; DOM ready",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-2",
            description="Page title or heading matches expected product identity",
            lifecycle_section="initial_rendering",
            acceptance_signal="document.title or h1 contains expected text",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-3",
            description="Login form container is visible in the viewport",
            lifecycle_section="initial_rendering",
            acceptance_signal="Login form element is visible and not hidden",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-4",
            description="Email and password input fields are present and enabled",
            lifecycle_section="initial_rendering",
            acceptance_signal="Both input elements have visible and enabled state",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-5",
            description="Submit/login button is present and actionable",
            lifecycle_section="initial_rendering",
            acceptance_signal="Button element is visible, not disabled",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-6",
            description="Viewport renders correctly at specified width/height",
            lifecycle_section="initial_rendering",
            acceptance_signal="No horizontal scroll, elements within viewport bounds",
            applicability=ApplicabilityEnum.applicable,
        ),
        # Interactions (FR-7..FR-12)
        RequirementSpec(
            fr_id="FR-7",
            description="Email field accepts keyboard input and retains value",
            lifecycle_section="interactions",
            acceptance_signal="Typed text appears in email input field",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-8",
            description="Password field accepts input and masks characters",
            lifecycle_section="interactions",
            acceptance_signal="Input type is password; characters are masked",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-9",
            description="Fields can be cleared and re-filled",
            lifecycle_section="interactions",
            acceptance_signal="After clear(), field value is empty; re-fill accepted",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-10",
            description="Input fields display placeholder text when empty",
            lifecycle_section="interactions",
            acceptance_signal="Placeholder attribute is present and visible when empty",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-11",
            description="Tab key moves focus between form fields in order",
            lifecycle_section="interactions",
            acceptance_signal="Focus moves from email → password → button on Tab",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-12",
            description="Submit button is disabled or shows loading state during submission",
            lifecycle_section="interactions",
            acceptance_signal="Button not clickable or has aria-busy=true during request",
            applicability=ApplicabilityEnum.optional,
        ),
        # Navigation (FR-13..FR-16)
        RequirementSpec(
            fr_id="FR-13",
            description="Form submission triggers a network request to the auth endpoint",
            lifecycle_section="navigation",
            acceptance_signal="XHR/fetch request observed on form submit",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-14",
            description="Successful login redirects user to an authenticated page",
            lifecycle_section="navigation",
            acceptance_signal="URL changes away from login path after valid credentials",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-15",
            description="Back navigation from authenticated page returns to authenticated state",
            lifecycle_section="navigation",
            acceptance_signal="Browser back does not show login form for active session",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-16",
            description="Session persists across page refresh after login",
            lifecycle_section="navigation",
            acceptance_signal="Refresh on authenticated page stays authenticated",
            applicability=ApplicabilityEnum.applicable,
        ),
        # Credential / Input Flows (FR-17..FR-24)
        RequirementSpec(
            fr_id="FR-17",
            description="Valid email and password produces a successful login outcome",
            lifecycle_section="credential_input_flows",
            acceptance_signal="No error shown; user reaches authenticated destination",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-18",
            description="Empty email field submission is rejected with feedback",
            lifecycle_section="credential_input_flows",
            acceptance_signal="Validation error or browser constraint prevents submission",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-19",
            description="Empty password field submission is rejected with feedback",
            lifecycle_section="credential_input_flows",
            acceptance_signal="Validation error or browser constraint prevents submission",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-20",
            description="Malformed email format is rejected at validation",
            lifecycle_section="credential_input_flows",
            acceptance_signal="Error message displayed for invalid email format",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-21",
            description="Correct email with wrong password is rejected",
            lifecycle_section="credential_input_flows",
            acceptance_signal="Error message shown; user remains on login page",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-22",
            description="Partial credential submission (one field empty) is rejected",
            lifecycle_section="credential_input_flows",
            acceptance_signal="Form does not submit; appropriate error shown",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-23",
            description="Credentials with leading/trailing whitespace are handled gracefully",
            lifecycle_section="credential_input_flows",
            acceptance_signal="Whitespace is trimmed or appropriate error shown",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-24",
            description="Email field is case-insensitive for authentication",
            lifecycle_section="credential_input_flows",
            acceptance_signal="UPPER and lower case email both succeed with valid password",
            applicability=ApplicabilityEnum.applicable,
        ),
        # Error / Recovery (FR-25..FR-32)
        RequirementSpec(
            fr_id="FR-25",
            description="Error message is visible and readable after failed login",
            lifecycle_section="error_recovery",
            acceptance_signal="Error element is visible with non-empty text content",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-26",
            description="Error message can be dismissed or clears on new input",
            lifecycle_section="error_recovery",
            acceptance_signal="Error disappears after user interaction or dismiss action",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-27",
            description="User can retry login after a failed attempt",
            lifecycle_section="error_recovery",
            acceptance_signal="Form is still interactive and submittable after failure",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-28",
            description="Locked account shows specific feedback message",
            lifecycle_section="error_recovery",
            acceptance_signal="Error text mentions account lock or contact support",
            applicability=ApplicabilityEnum.optional,
        ),
        RequirementSpec(
            fr_id="FR-29",
            description="Delayed rendering does not break form interactivity",
            lifecycle_section="error_recovery",
            acceptance_signal="Form elements are usable after any loading overlay disappears",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-30",
            description="Empty-state placeholder or welcome message shown before first interaction",
            lifecycle_section="error_recovery",
            acceptance_signal="Page shows expected initial content with no user action",
            applicability=ApplicabilityEnum.applicable,
        ),
        RequirementSpec(
            fr_id="FR-31",
            description="Correct credentials after prior failure produces successful login",
            lifecycle_section="error_recovery",
            acceptance_signal="Second attempt with valid creds succeeds and redirects",
            applicability=ApplicabilityEnum.required,
        ),
        RequirementSpec(
            fr_id="FR-32",
            description="Network error during submission shows appropriate error state",
            lifecycle_section="error_recovery",
            acceptance_signal="Network error results in visible error message, not a blank page",
            applicability=ApplicabilityEnum.applicable,
        ),
    ]
    return [s.model_dump() for s in specs]


class CredentialValidationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CredentialValidationRepository(db)

    # ─── Definitions ─────────────────────────────────────────────────────────

    async def create_definition(self, data: DefinitionCreate) -> DefinitionResponse:
        payload = data.model_dump()
        if not payload.get("requirements"):
            payload["requirements"] = _build_default_requirements()
        obj = await self.repo.create_definition(payload)
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("credential_validation.definition.created", id=str(obj.id), name=obj.name)
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
        logger.info("credential_validation.definition.updated", id=str(obj.id))
        return DefinitionResponse.model_validate(obj)

    async def delete_definition(self, definition_id: uuid.UUID) -> None:
        deleted = await self.repo.delete_definition(definition_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Definition not found")
        await self.db.commit()
        logger.info("credential_validation.definition.deleted", id=str(definition_id))

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
        obj = await self.repo.create_execution(payload)
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("credential_validation.execution.created", id=str(obj.id))
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

        updated = await self.repo.update_execution(execution_id, payload)
        await self.db.commit()
        await self.db.refresh(updated)
        logger.info("credential_validation.execution.updated", id=str(execution_id))
        return ExecutionResponse.model_validate(updated)
