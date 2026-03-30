"""Pydantic v2 schemas for credential validation."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.login_mgmt.login_flow_backend.credential_validation.models import (
    CoverageArea,
    ExecutionStatus,
    RuleType,
)


# ── Scenario schemas ──────────────────────────────────────────────────────────

class ScenarioCreate(BaseModel):
    page_url: str = Field(..., min_length=1, max_length=2048)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    coverage_area: CoverageArea
    requirement_ref: Optional[str] = Field(None, max_length=50)
    is_active: bool = True


class ScenarioUpdate(BaseModel):
    page_url: Optional[str] = Field(None, min_length=1, max_length=2048)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    coverage_area: Optional[CoverageArea] = None
    requirement_ref: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class ScenarioResponse(BaseModel):
    id: UUID
    page_url: str
    name: str
    description: Optional[str]
    coverage_area: CoverageArea
    requirement_ref: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Rule schemas ──────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    rule_type: RuleType
    selector: Optional[str] = Field(None, max_length=512)
    expected_value: Optional[str] = None
    description: Optional[str] = None


class RuleUpdate(BaseModel):
    rule_type: Optional[RuleType] = None
    selector: Optional[str] = Field(None, max_length=512)
    expected_value: Optional[str] = None
    description: Optional[str] = None


class RuleResponse(BaseModel):
    id: UUID
    scenario_id: UUID
    rule_type: RuleType
    selector: Optional[str]
    expected_value: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Execution schemas ─────────────────────────────────────────────────────────

class ExecutionCreate(BaseModel):
    pass


class ExecutionStatusUpdate(BaseModel):
    status: ExecutionStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    total_rules: Optional[int] = Field(None, ge=0)
    passed_rules: Optional[int] = Field(None, ge=0)
    failed_rules: Optional[int] = Field(None, ge=0)


class ExecutionResponse(BaseModel):
    id: UUID
    scenario_id: UUID
    status: ExecutionStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_rules: int
    passed_rules: int
    failed_rules: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExecutionSummary(BaseModel):
    execution_id: UUID
    scenario_id: UUID
    status: ExecutionStatus
    total_rules: int
    passed_rules: int
    failed_rules: int
    pass_rate: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Result schemas ────────────────────────────────────────────────────────────

class ResultCreate(BaseModel):
    rule_id: UUID
    passed: bool
    actual_value: Optional[str] = None
    error_message: Optional[str] = None


class ResultResponse(BaseModel):
    id: UUID
    execution_id: UUID
    rule_id: UUID
    passed: bool
    actual_value: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Pagination wrapper ────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    pages: int


# ── Filter params ─────────────────────────────────────────────────────────────

class ScenarioFilterParams(BaseModel):
    coverage_area: Optional[CoverageArea] = None
    is_active: Optional[bool] = None
    requirement_ref: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: str = Field("created_at", pattern="^(name|created_at|updated_at|coverage_area)$")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")
