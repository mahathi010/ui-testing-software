"""Pydantic v2 schemas for credential validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApplicabilityEnum(str, Enum):
    applicable = "applicable"
    required = "required"
    optional = "optional"
    blocked = "blocked"
    not_observed = "not_observed"


class ExecutionStatusEnum(str, Enum):
    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"
    error = "error"
    skipped = "skipped"


class RequirementSpec(BaseModel):
    fr_id: str
    description: str
    lifecycle_section: str
    acceptance_signal: str
    applicability: ApplicabilityEnum = ApplicabilityEnum.applicable
    is_required: bool = True

    model_config = {"from_attributes": True}


# ─── Definition Schemas ───────────────────────────────────────────────────────

class DefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    target_url: str
    version: Optional[str] = None
    page_identity_indicator: Optional[str] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    visible_sections: Optional[Any] = None
    actionable_controls: Optional[Any] = None
    visible_inputs: Optional[Any] = None
    credential_controls: Optional[Any] = None
    valid_credential_scenarios: Optional[Any] = None
    invalid_credential_combinations: Optional[Any] = None
    validation_feedback_expectations: Optional[Any] = None
    success_outcomes: Optional[Any] = None
    error_feedback_expectations: Optional[Any] = None
    empty_state_expectations: Optional[Any] = None
    navigation_expectations: Optional[Any] = None
    requirements: Optional[List[RequirementSpec]] = None
    clean_session_required: bool = True
    delayed_rendering_behavior: Optional[Any] = None
    retry_behavior: Optional[Any] = None
    recovery_conditions: Optional[Any] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class DefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_url: Optional[str] = None
    version: Optional[str] = None
    page_identity_indicator: Optional[str] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    visible_sections: Optional[Any] = None
    actionable_controls: Optional[Any] = None
    visible_inputs: Optional[Any] = None
    credential_controls: Optional[Any] = None
    valid_credential_scenarios: Optional[Any] = None
    invalid_credential_combinations: Optional[Any] = None
    validation_feedback_expectations: Optional[Any] = None
    success_outcomes: Optional[Any] = None
    error_feedback_expectations: Optional[Any] = None
    empty_state_expectations: Optional[Any] = None
    navigation_expectations: Optional[Any] = None
    requirements: Optional[List[RequirementSpec]] = None
    clean_session_required: Optional[bool] = None
    delayed_rendering_behavior: Optional[Any] = None
    retry_behavior: Optional[Any] = None
    recovery_conditions: Optional[Any] = None
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}


class DefinitionResponse(BaseModel):
    id: UUID
    name: str
    target_url: str
    version: Optional[str] = None
    page_identity_indicator: Optional[str] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    visible_sections: Optional[Any] = None
    actionable_controls: Optional[Any] = None
    visible_inputs: Optional[Any] = None
    credential_controls: Optional[Any] = None
    valid_credential_scenarios: Optional[Any] = None
    invalid_credential_combinations: Optional[Any] = None
    validation_feedback_expectations: Optional[Any] = None
    success_outcomes: Optional[Any] = None
    error_feedback_expectations: Optional[Any] = None
    empty_state_expectations: Optional[Any] = None
    navigation_expectations: Optional[Any] = None
    requirements: Optional[Any] = None
    clean_session_required: bool
    delayed_rendering_behavior: Optional[Any] = None
    retry_behavior: Optional[Any] = None
    recovery_conditions: Optional[Any] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Execution Schemas ────────────────────────────────────────────────────────

class ExecutionCreate(BaseModel):
    definition_id: UUID
    target_url: Optional[str] = None
    target_version: Optional[str] = None
    status: ExecutionStatusEnum = ExecutionStatusEnum.pending
    summary_outcome: Optional[Any] = None
    requirement_results: Optional[Any] = None
    failure_details: Optional[Any] = None
    recovery_details: Optional[Any] = None

    model_config = {"from_attributes": True}


class ExecutionUpdate(BaseModel):
    target_url: Optional[str] = None
    target_version: Optional[str] = None
    status: Optional[ExecutionStatusEnum] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    summary_outcome: Optional[Any] = None
    requirement_results: Optional[Any] = None
    failure_details: Optional[Any] = None
    recovery_details: Optional[Any] = None

    model_config = {"from_attributes": True}


class ExecutionResponse(BaseModel):
    id: UUID
    definition_id: UUID
    target_url: Optional[str] = None
    target_version: Optional[str] = None
    status: ExecutionStatusEnum
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    summary_outcome: Optional[Any] = None
    requirement_results: Optional[Any] = None
    failure_details: Optional[Any] = None
    recovery_details: Optional[Any] = None
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
