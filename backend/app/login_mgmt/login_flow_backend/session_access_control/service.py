"""Business logic for session access control. Service owns transactions (commit)."""

import uuid
from typing import Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AccessOutcome, ActionType, ProtectionLevel, SessionStatus
from .repository import SessionAccessControlRepository
from .schema import (
    AccessOutcomeEnum,
    AccessRecordCreate,
    AccessRecordResponse,
    ActionTypeEnum,
    GuardedActionRequest,
    GuardedActionResponse,
    PaginatedResponse,
    ProtectionLevelEnum,
    ResourceCreate,
    ResourceResponse,
    ResourceUpdate,
    SessionCheckRequest,
    SessionCheckResponse,
    SessionStatusEnum,
)

logger = structlog.get_logger(__name__)

_SUPPORTED_RESOURCE_FILTERS = {"is_active", "protection_level", "resource_name"}
_SUPPORTED_RECORD_FILTERS = {"resource_id", "session_status", "outcome"}


def _resolve_session_status(token: Optional[str]) -> SessionStatusEnum:
    """Determine session status from token prefix semantics."""
    if not token:
        return SessionStatusEnum.anonymous
    if token.startswith("valid_"):
        return SessionStatusEnum.active
    if token.startswith("expired_"):
        return SessionStatusEnum.expired
    return SessionStatusEnum.invalid


def _determine_outcome(
    session_status: SessionStatusEnum,
    protection_level: ProtectionLevelEnum,
) -> tuple[AccessOutcomeEnum, Optional[str], Optional[str]]:
    """Return (outcome, denial_reason, redirect_url) for the given session × protection combination."""
    if session_status == SessionStatusEnum.anonymous:
        if protection_level == ProtectionLevelEnum.public:
            return AccessOutcomeEnum.allowed, None, None
        return AccessOutcomeEnum.denied_guest, "Authentication required", "/login"

    if session_status == SessionStatusEnum.active:
        if protection_level in (ProtectionLevelEnum.public, ProtectionLevelEnum.authenticated):
            return AccessOutcomeEnum.allowed, None, None
        return AccessOutcomeEnum.denied_forbidden, "Elevated privileges required", None

    if session_status == SessionStatusEnum.expired:
        if protection_level == ProtectionLevelEnum.public:
            return AccessOutcomeEnum.allowed, None, None
        return AccessOutcomeEnum.denied_expired, "Session has expired", "/login"

    # invalid
    if protection_level == ProtectionLevelEnum.public:
        return AccessOutcomeEnum.allowed, None, None
    return AccessOutcomeEnum.denied_invalid, "Session token is invalid", None


class SessionAccessControlService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SessionAccessControlRepository(db)

    # ─── Session Checks ───────────────────────────────────────────────────────

    async def check_session_access(self, data: SessionCheckRequest) -> SessionCheckResponse:
        session_status = _resolve_session_status(data.session_token)

        resource = await self.repo.get_resource_by_path(data.resource_path)
        protection_level = (
            ProtectionLevelEnum(resource.protection_level.value)
            if resource
            else ProtectionLevelEnum.public
        )

        outcome, denial_reason, redirect_url = _determine_outcome(session_status, protection_level)
        is_valid = outcome == AccessOutcomeEnum.allowed

        record_data = {
            "resource_id": resource.id if resource else None,
            "session_token": data.session_token,
            "session_status": session_status.value,
            "action_type": data.action_type.value,
            "outcome": outcome.value,
            "denial_reason": denial_reason,
            "redirect_url": redirect_url,
        }
        record = await self.repo.create_record(record_data)
        await self.db.commit()
        await self.db.refresh(record)

        logger.info(
            "session_access_control.check",
            session_status=session_status,
            outcome=outcome,
            resource_path=data.resource_path,
        )
        return SessionCheckResponse(
            is_valid=is_valid,
            session_status=session_status,
            outcome=outcome,
            redirect_url=redirect_url,
            denial_reason=denial_reason,
            record_id=record.id,
        )

    async def attempt_guarded_action(self, data: GuardedActionRequest) -> GuardedActionResponse:
        session_status = _resolve_session_status(data.session_token)

        resource = await self.repo.get_resource_by_path(data.resource_path)
        protection_level = (
            ProtectionLevelEnum(resource.protection_level.value)
            if resource
            else ProtectionLevelEnum.authenticated
        )

        outcome, denial_reason, redirect_url = _determine_outcome(session_status, protection_level)
        allowed = outcome == AccessOutcomeEnum.allowed

        record_data = {
            "resource_id": resource.id if resource else None,
            "session_token": data.session_token,
            "session_status": session_status.value,
            "action_type": ActionType.guarded_action.value,
            "outcome": outcome.value,
            "denial_reason": denial_reason,
            "redirect_url": redirect_url,
            "request_metadata": data.request_metadata,
        }
        record = await self.repo.create_record(record_data)
        await self.db.commit()
        await self.db.refresh(record)

        logger.info(
            "session_access_control.guarded_action",
            session_status=session_status,
            outcome=outcome,
            resource_path=data.resource_path,
        )
        return GuardedActionResponse(
            allowed=allowed,
            session_status=session_status,
            outcome=outcome,
            denial_reason=denial_reason,
            redirect_url=redirect_url,
            record_id=record.id,
        )

    # ─── Resources ────────────────────────────────────────────────────────────

    async def create_resource(self, data: ResourceCreate) -> ResourceResponse:
        payload = data.model_dump()
        payload["protection_level"] = payload["protection_level"].value
        obj = await self.repo.create_resource(payload)
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("session_access_control.resource.created", id=str(obj.id), name=obj.resource_name)
        return ResourceResponse.model_validate(obj)

    async def get_resource(self, resource_id: uuid.UUID) -> ResourceResponse:
        obj = await self.repo.get_resource(resource_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        return ResourceResponse.model_validate(obj)

    async def list_resources(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> PaginatedResponse[ResourceResponse]:
        if filters:
            unsupported = set(filters.keys()) - _SUPPORTED_RESOURCE_FILTERS
            if unsupported:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported filter keys: {sorted(unsupported)}",
                )
        items, total = await self.repo.list_resources(page, page_size, sort_by, sort_dir, filters)
        return PaginatedResponse(
            items=[ResourceResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_resource(
        self, resource_id: uuid.UUID, data: ResourceUpdate
    ) -> ResourceResponse:
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        if "protection_level" in payload and isinstance(payload["protection_level"], ProtectionLevelEnum):
            payload["protection_level"] = payload["protection_level"].value
        obj = await self.repo.update_resource(resource_id, payload)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("session_access_control.resource.updated", id=str(resource_id))
        return ResourceResponse.model_validate(obj)

    async def delete_resource(self, resource_id: uuid.UUID) -> None:
        deleted = await self.repo.delete_resource(resource_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        await self.db.commit()
        logger.info("session_access_control.resource.deleted", id=str(resource_id))

    # ─── Records ──────────────────────────────────────────────────────────────

    async def create_record(self, data: AccessRecordCreate) -> AccessRecordResponse:
        payload = data.model_dump()
        payload["session_status"] = payload["session_status"].value
        payload["action_type"] = payload["action_type"].value
        payload["outcome"] = payload["outcome"].value
        obj = await self.repo.create_record(payload)
        await self.db.commit()
        await self.db.refresh(obj)
        logger.info("session_access_control.record.created", id=str(obj.id))
        return AccessRecordResponse.model_validate(obj)

    async def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> PaginatedResponse[AccessRecordResponse]:
        if filters:
            unsupported = set(filters.keys()) - _SUPPORTED_RECORD_FILTERS
            if unsupported:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported filter keys: {sorted(unsupported)}",
                )
        items, total = await self.repo.list_records(page, page_size, sort_by, sort_dir, filters)
        return PaginatedResponse(
            items=[AccessRecordResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )
