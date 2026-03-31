"""Pydantic v2 schemas for session access control."""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class ProtectionLevelEnum(str, Enum):
    public = "public"
    authenticated = "authenticated"
    elevated = "elevated"


class SessionStatusEnum(str, Enum):
    active = "active"
    expired = "expired"
    invalid = "invalid"
    anonymous = "anonymous"


class ActionTypeEnum(str, Enum):
    page_view = "page_view"
    guarded_action = "guarded_action"
    navigation = "navigation"
    media_access = "media_access"


class AccessOutcomeEnum(str, Enum):
    allowed = "allowed"
    denied_guest = "denied_guest"
    denied_expired = "denied_expired"
    denied_invalid = "denied_invalid"
    denied_forbidden = "denied_forbidden"
    redirected = "redirected"
    error = "error"


# ─── Resource Schemas ─────────────────────────────────────────────────────────

class ResourceCreate(BaseModel):
    resource_path: str = Field(..., min_length=1)
    resource_name: str = Field(..., min_length=1, max_length=255)
    protection_level: ProtectionLevelEnum = ProtectionLevelEnum.authenticated
    description: Optional[str] = None
    session_requirements: Optional[Any] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class ResourceUpdate(BaseModel):
    resource_path: Optional[str] = None
    resource_name: Optional[str] = Field(None, min_length=1, max_length=255)
    protection_level: Optional[ProtectionLevelEnum] = None
    description: Optional[str] = None
    session_requirements: Optional[Any] = None
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}


class ResourceResponse(BaseModel):
    id: UUID
    resource_path: str
    resource_name: str
    protection_level: ProtectionLevelEnum
    description: Optional[str] = None
    session_requirements: Optional[Any] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Session Check Schemas ────────────────────────────────────────────────────

class SessionCheckRequest(BaseModel):
    session_token: Optional[str] = None
    resource_path: str
    action_type: ActionTypeEnum = ActionTypeEnum.page_view

    model_config = {"from_attributes": True}


class SessionCheckResponse(BaseModel):
    is_valid: bool
    session_status: SessionStatusEnum
    outcome: AccessOutcomeEnum
    redirect_url: Optional[str] = None
    denial_reason: Optional[str] = None
    record_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


# ─── Guarded Action Schemas ───────────────────────────────────────────────────

class GuardedActionRequest(BaseModel):
    session_token: Optional[str] = None
    resource_path: str
    action_description: Optional[str] = None
    request_metadata: Optional[Any] = None

    model_config = {"from_attributes": True}


class GuardedActionResponse(BaseModel):
    allowed: bool
    session_status: SessionStatusEnum
    outcome: AccessOutcomeEnum
    denial_reason: Optional[str] = None
    redirect_url: Optional[str] = None
    record_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


# ─── Access Record Schemas ────────────────────────────────────────────────────

class AccessRecordCreate(BaseModel):
    resource_id: Optional[UUID] = None
    session_token: Optional[str] = None
    session_status: SessionStatusEnum = SessionStatusEnum.anonymous
    user_identifier: Optional[str] = None
    action_type: ActionTypeEnum = ActionTypeEnum.page_view
    outcome: AccessOutcomeEnum = AccessOutcomeEnum.allowed
    denial_reason: Optional[str] = None
    redirect_url: Optional[str] = None
    request_metadata: Optional[Any] = None

    model_config = {"from_attributes": True}


class AccessRecordResponse(BaseModel):
    id: UUID
    resource_id: Optional[UUID] = None
    session_token: Optional[str] = None
    session_status: SessionStatusEnum
    user_identifier: Optional[str] = None
    action_type: ActionTypeEnum
    outcome: AccessOutcomeEnum
    denial_reason: Optional[str] = None
    redirect_url: Optional[str] = None
    request_metadata: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Pagination / Errors ──────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
