"""Business logic for credential validation — owns commit(), raises HTTPException."""

from typing import List, Optional, Tuple
from uuid import UUID

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.login_mgmt.login_flow_backend.credential_validation.models import (
    CoverageArea,
    ExecutionStatus,
)
from app.login_mgmt.login_flow_backend.credential_validation.repository import (
    ExecutionRepository,
    ResultRepository,
    RuleRepository,
    ScenarioRepository,
)
from app.login_mgmt.login_flow_backend.credential_validation.schema import (
    ExecutionStatusUpdate,
    ResultCreate,
    RuleCreate,
    RuleUpdate,
    ScenarioCreate,
    ScenarioFilterParams,
    ScenarioUpdate,
)

logger = structlog.get_logger(__name__)


class CredentialValidationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.scenario_repo = ScenarioRepository(db)
        self.rule_repo = RuleRepository(db)
        self.execution_repo = ExecutionRepository(db)
        self.result_repo = ResultRepository(db)

    # ── Scenarios ─────────────────────────────────────────────────────────────

    async def list_scenarios(self, filters: ScenarioFilterParams):
        items, total = await self.scenario_repo.find_all(
            coverage_area=filters.coverage_area,
            is_active=filters.is_active,
            requirement_ref=filters.requirement_ref,
            page=filters.page,
            page_size=filters.page_size,
            sort_by=filters.sort_by,
            sort_order=filters.sort_order,
        )
        pages = max(1, (total + filters.page_size - 1) // filters.page_size)
        return items, total, pages

    async def get_scenario(self, scenario_id: UUID):
        scenario = await self.scenario_repo.find_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return scenario

    async def create_scenario(self, data: ScenarioCreate):
        scenario = await self.scenario_repo.create(data.model_dump())
        await self.db.commit()
        logger.info("scenario_created", scenario_id=str(scenario.id), name=scenario.name)
        return scenario

    async def update_scenario(self, scenario_id: UUID, data: ScenarioUpdate):
        scenario = await self.get_scenario(scenario_id)
        updated = await self.scenario_repo.update(scenario, data.model_dump(exclude_none=True))
        await self.db.commit()
        logger.info("scenario_updated", scenario_id=str(scenario_id))
        return updated

    async def delete_scenario(self, scenario_id: UUID) -> None:
        scenario = await self.get_scenario(scenario_id)
        await self.scenario_repo.delete(scenario)
        await self.db.commit()
        logger.info("scenario_deleted", scenario_id=str(scenario_id))

    # ── Rules ──────────────────────────────────────────────────────────────────

    async def list_rules(self, scenario_id: UUID):
        await self.get_scenario(scenario_id)
        return await self.rule_repo.find_by_scenario(scenario_id)

    async def get_rule(self, scenario_id: UUID, rule_id: UUID):
        await self.get_scenario(scenario_id)
        rule = await self.rule_repo.find_by_id_and_scenario(rule_id, scenario_id)
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
        return rule

    async def create_rule(self, scenario_id: UUID, data: RuleCreate):
        await self.get_scenario(scenario_id)
        rule_data = data.model_dump()
        rule_data["scenario_id"] = scenario_id
        rule = await self.rule_repo.create(rule_data)
        await self.db.commit()
        logger.info("rule_created", rule_id=str(rule.id), scenario_id=str(scenario_id))
        return rule

    async def update_rule(self, scenario_id: UUID, rule_id: UUID, data: RuleUpdate):
        rule = await self.get_rule(scenario_id, rule_id)
        updated = await self.rule_repo.update(rule, data.model_dump(exclude_none=True))
        await self.db.commit()
        logger.info("rule_updated", rule_id=str(rule_id))
        return updated

    async def delete_rule(self, scenario_id: UUID, rule_id: UUID) -> None:
        rule = await self.get_rule(scenario_id, rule_id)
        await self.rule_repo.delete(rule)
        await self.db.commit()
        logger.info("rule_deleted", rule_id=str(rule_id))

    # ── Executions ─────────────────────────────────────────────────────────────

    async def list_executions(self, scenario_id: UUID):
        await self.get_scenario(scenario_id)
        return await self.execution_repo.find_by_scenario(scenario_id)

    async def get_execution(self, scenario_id: UUID, execution_id: UUID):
        await self.get_scenario(scenario_id)
        execution = await self.execution_repo.find_by_id_and_scenario(execution_id, scenario_id)
        if execution is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
        return execution

    async def create_execution(self, scenario_id: UUID):
        await self.get_scenario(scenario_id)
        execution = await self.execution_repo.create(
            {"scenario_id": scenario_id, "status": ExecutionStatus.PENDING}
        )
        await self.db.commit()
        logger.info("execution_created", execution_id=str(execution.id), scenario_id=str(scenario_id))
        return execution

    async def update_execution_status(self, scenario_id: UUID, execution_id: UUID, data: ExecutionStatusUpdate):
        execution = await self.get_execution(scenario_id, execution_id)
        update_data = data.model_dump(exclude_none=True)
        updated = await self.execution_repo.update(execution, update_data)
        await self.db.commit()
        logger.info("execution_status_updated", execution_id=str(execution_id), status=data.status)
        return updated

    async def get_execution_summary(self, scenario_id: UUID, execution_id: UUID):
        execution = await self.get_execution(scenario_id, execution_id)
        total, passed, failed = await self.result_repo.count_by_execution(execution_id)
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        return {
            "execution_id": execution.id,
            "scenario_id": execution.scenario_id,
            "status": execution.status,
            "total_rules": total,
            "passed_rules": passed,
            "failed_rules": failed,
            "pass_rate": pass_rate,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
        }

    # ── Results ────────────────────────────────────────────────────────────────

    async def list_results(self, scenario_id: UUID, execution_id: UUID):
        await self.get_execution(scenario_id, execution_id)
        return await self.result_repo.find_by_execution(execution_id)

    async def record_result(self, scenario_id: UUID, execution_id: UUID, data: ResultCreate):
        await self.get_execution(scenario_id, execution_id)
        # Verify rule belongs to the scenario
        rule = await self.rule_repo.find_by_id_and_scenario(data.rule_id, scenario_id)
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found in this scenario",
            )
        result_data = data.model_dump()
        result_data["execution_id"] = execution_id
        result = await self.result_repo.create(result_data)
        await self.db.commit()
        logger.info("result_recorded", result_id=str(result.id), execution_id=str(execution_id), passed=data.passed)
        return result
