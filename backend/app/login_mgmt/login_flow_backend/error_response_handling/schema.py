"""Pydantic v2 schemas for error response handling."""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class ExecutionStatusEnum(str, Enum):
    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"
    error = "error"
    skipped = "skipped"


# ─── Definition Schemas ───────────────────────────────────────────────────────

class ErrorResponseDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    target_url: str
    version: Optional[str] = None
    page_identity_indicator: Optional[str] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    visible_sections: Optional[Any] = None
    actionable_controls: Optional[Any] = None
    error_response_scenarios: Optional[Any] = None
    empty_state_expectations: Optional[Any] = None
    invalid_content_expectations: Optional[Any] = None
    loading_state_expectations: Optional[Any] = None
    recovery_conditions: Optional[Any] = None
    requirements: Optional[Any] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class ErrorResponseDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_url: Optional[str] = None
    version: Optional[str] = None
    page_identity_indicator: Optional[str] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    visible_sections: Optional[Any] = None
    actionable_controls: Optional[Any] = None
    error_response_scenarios: Optional[Any] = None
    empty_state_expectations: Optional[Any] = None
    invalid_content_expectations: Optional[Any] = None
    loading_state_expectations: Optional[Any] = None
    recovery_conditions: Optional[Any] = None
    requirements: Optional[Any] = None
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}


class ErrorResponseDefinitionResponse(BaseModel):
    id: UUID
    name: str
    target_url: str
    version: Optional[str] = None
    page_identity_indicator: Optional[str] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    visible_sections: Optional[Any] = None
    actionable_controls: Optional[Any] = None
    error_response_scenarios: Optional[Any] = None
    empty_state_expectations: Optional[Any] = None
    invalid_content_expectations: Optional[Any] = None
    loading_state_expectations: Optional[Any] = None
    recovery_conditions: Optional[Any] = None
    requirements: Optional[Any] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Execution Schemas ────────────────────────────────────────────────────────

class ErrorResponseExecutionCreate(BaseModel):
    definition_id: UUID
    status: ExecutionStatusEnum = ExecutionStatusEnum.pending
    summary_outcome: Optional[Any] = None
    requirement_results: Optional[Any] = None
    failure_details: Optional[Any] = None
    recovery_details: Optional[Any] = None

    model_config = {"from_attributes": True}


class ErrorResponseExecutionUpdate(BaseModel):
    status: Optional[ExecutionStatusEnum] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    summary_outcome: Optional[Any] = None
    requirement_results: Optional[Any] = None
    failure_details: Optional[Any] = None
    recovery_details: Optional[Any] = None

    model_config = {"from_attributes": True}


class ErrorResponseExecutionResponse(BaseModel):
    id: UUID
    definition_id: UUID
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


# ─── Pagination ───────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int

    model_config = {"from_attributes": True}
