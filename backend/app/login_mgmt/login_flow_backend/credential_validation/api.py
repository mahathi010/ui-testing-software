"""FastAPI router for credential validation — /v1/credential-validations."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.login_mgmt.login_flow_backend.credential_validation.models import CoverageArea
from app.login_mgmt.login_flow_backend.credential_validation.schema import (
    ExecutionResponse,
    ExecutionStatusUpdate,
    ExecutionSummary,
    PaginatedResponse,
    ResultCreate,
    ResultResponse,
    RuleCreate,
    RuleResponse,
    RuleUpdate,
    ScenarioCreate,
    ScenarioFilterParams,
    ScenarioResponse,
    ScenarioUpdate,
)
from app.login_mgmt.login_flow_backend.credential_validation.service import (
    CredentialValidationService,
)

router = APIRouter(prefix="/v1/credential-validations", tags=["credential-validations"])


def get_service(db: AsyncSession = Depends(get_db)) -> CredentialValidationService:
    return CredentialValidationService(db)


# ── Scenario endpoints ────────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedResponse, summary="List scenarios")
async def list_scenarios(
    coverage_area: Optional[CoverageArea] = Query(None),
    is_active: Optional[bool] = Query(None),
    requirement_ref: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", pattern="^(name|created_at|updated_at|coverage_area)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    svc: CredentialValidationService = Depends(get_service),
):
    filters = ScenarioFilterParams(
        coverage_area=coverage_area,
        is_active=is_active,
        requirement_ref=requirement_ref,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    items, total, pages = await svc.list_scenarios(filters)
    return PaginatedResponse(
        items=[ScenarioResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED, summary="Create scenario")
async def create_scenario(
    data: ScenarioCreate,
    svc: CredentialValidationService = Depends(get_service),
):
    scenario = await svc.create_scenario(data)
    return ScenarioResponse.model_validate(scenario)


@router.get("/{scenario_id}", response_model=ScenarioResponse, summary="Get scenario")
async def get_scenario(
    scenario_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    scenario = await svc.get_scenario(scenario_id)
    return ScenarioResponse.model_validate(scenario)


@router.put("/{scenario_id}", response_model=ScenarioResponse, summary="Update scenario")
async def update_scenario(
    scenario_id: UUID,
    data: ScenarioUpdate,
    svc: CredentialValidationService = Depends(get_service),
):
    scenario = await svc.update_scenario(scenario_id, data)
    return ScenarioResponse.model_validate(scenario)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete scenario")
async def delete_scenario(
    scenario_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    await svc.delete_scenario(scenario_id)


# ── Rule endpoints ────────────────────────────────────────────────────────────

@router.get("/{scenario_id}/rules", response_model=list[RuleResponse], summary="List rules")
async def list_rules(
    scenario_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    rules = await svc.list_rules(scenario_id)
    return [RuleResponse.model_validate(r) for r in rules]


@router.post("/{scenario_id}/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED, summary="Create rule")
async def create_rule(
    scenario_id: UUID,
    data: RuleCreate,
    svc: CredentialValidationService = Depends(get_service),
):
    rule = await svc.create_rule(scenario_id, data)
    return RuleResponse.model_validate(rule)


@router.get("/{scenario_id}/rules/{rule_id}", response_model=RuleResponse, summary="Get rule")
async def get_rule(
    scenario_id: UUID,
    rule_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    rule = await svc.get_rule(scenario_id, rule_id)
    return RuleResponse.model_validate(rule)


@router.put("/{scenario_id}/rules/{rule_id}", response_model=RuleResponse, summary="Update rule")
async def update_rule(
    scenario_id: UUID,
    rule_id: UUID,
    data: RuleUpdate,
    svc: CredentialValidationService = Depends(get_service),
):
    rule = await svc.update_rule(scenario_id, rule_id, data)
    return RuleResponse.model_validate(rule)


@router.delete("/{scenario_id}/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete rule")
async def delete_rule(
    scenario_id: UUID,
    rule_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    await svc.delete_rule(scenario_id, rule_id)


# ── Execution endpoints ───────────────────────────────────────────────────────

@router.post("/{scenario_id}/executions", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED, summary="Create execution")
async def create_execution(
    scenario_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    execution = await svc.create_execution(scenario_id)
    return ExecutionResponse.model_validate(execution)


@router.get("/{scenario_id}/executions", response_model=list[ExecutionResponse], summary="List executions")
async def list_executions(
    scenario_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    executions = await svc.list_executions(scenario_id)
    return [ExecutionResponse.model_validate(e) for e in executions]


@router.get("/{scenario_id}/executions/{execution_id}", response_model=ExecutionResponse, summary="Get execution")
async def get_execution(
    scenario_id: UUID,
    execution_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    execution = await svc.get_execution(scenario_id, execution_id)
    return ExecutionResponse.model_validate(execution)


@router.patch("/{scenario_id}/executions/{execution_id}", response_model=ExecutionResponse, summary="Update execution status")
async def update_execution_status(
    scenario_id: UUID,
    execution_id: UUID,
    data: ExecutionStatusUpdate,
    svc: CredentialValidationService = Depends(get_service),
):
    execution = await svc.update_execution_status(scenario_id, execution_id, data)
    return ExecutionResponse.model_validate(execution)


@router.get("/{scenario_id}/executions/{execution_id}/summary", response_model=ExecutionSummary, summary="Get execution summary")
async def get_execution_summary(
    scenario_id: UUID,
    execution_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    summary = await svc.get_execution_summary(scenario_id, execution_id)
    return ExecutionSummary.model_validate(summary)


# ── Result endpoints ──────────────────────────────────────────────────────────

@router.get("/{scenario_id}/executions/{execution_id}/results", response_model=list[ResultResponse], summary="List results")
async def list_results(
    scenario_id: UUID,
    execution_id: UUID,
    svc: CredentialValidationService = Depends(get_service),
):
    results = await svc.list_results(scenario_id, execution_id)
    return [ResultResponse.model_validate(r) for r in results]


@router.post("/{scenario_id}/executions/{execution_id}/results", response_model=ResultResponse, status_code=status.HTTP_201_CREATED, summary="Record result")
async def record_result(
    scenario_id: UUID,
    execution_id: UUID,
    data: ResultCreate,
    svc: CredentialValidationService = Depends(get_service),
):
    result = await svc.record_result(scenario_id, execution_id, data)
    return ResultResponse.model_validate(result)
