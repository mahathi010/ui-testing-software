"""Repository layer for credential validation — only flush(), no business logic."""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.login_mgmt.login_flow_backend.credential_validation.models import (
    CredentialValidationScenario,
    CoverageArea,
    ExecutionStatus,
    TestExecution,
    TestResult,
    ValidationRule,
)


class ScenarioRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_all(
        self,
        coverage_area: Optional[CoverageArea] = None,
        is_active: Optional[bool] = None,
        requirement_ref: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[CredentialValidationScenario], int]:
        query = select(CredentialValidationScenario)
        count_query = select(func.count(CredentialValidationScenario.id))

        if coverage_area is not None:
            query = query.where(CredentialValidationScenario.coverage_area == coverage_area)
            count_query = count_query.where(CredentialValidationScenario.coverage_area == coverage_area)
        if is_active is not None:
            query = query.where(CredentialValidationScenario.is_active == is_active)
            count_query = count_query.where(CredentialValidationScenario.is_active == is_active)
        if requirement_ref is not None:
            query = query.where(CredentialValidationScenario.requirement_ref == requirement_ref)
            count_query = count_query.where(CredentialValidationScenario.requirement_ref == requirement_ref)

        sort_col = getattr(CredentialValidationScenario, sort_by, CredentialValidationScenario.created_at)
        query = query.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))
        query = query.offset((page - 1) * page_size).limit(page_size)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query)
        items = result.scalars().all()
        return list(items), total

    async def find_by_id(self, scenario_id: UUID) -> Optional[CredentialValidationScenario]:
        result = await self.db.execute(
            select(CredentialValidationScenario).where(CredentialValidationScenario.id == scenario_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> CredentialValidationScenario:
        scenario = CredentialValidationScenario(**data)
        self.db.add(scenario)
        await self.db.flush()
        await self.db.refresh(scenario)
        return scenario

    async def update(self, scenario: CredentialValidationScenario, data: dict) -> CredentialValidationScenario:
        for key, value in data.items():
            setattr(scenario, key, value)
        await self.db.flush()
        await self.db.refresh(scenario)
        return scenario

    async def delete(self, scenario: CredentialValidationScenario) -> None:
        await self.db.delete(scenario)
        await self.db.flush()


class RuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_scenario(self, scenario_id: UUID) -> List[ValidationRule]:
        result = await self.db.execute(
            select(ValidationRule)
            .where(ValidationRule.scenario_id == scenario_id)
            .order_by(asc(ValidationRule.created_at))
        )
        return list(result.scalars().all())

    async def find_by_id(self, rule_id: UUID) -> Optional[ValidationRule]:
        result = await self.db.execute(
            select(ValidationRule).where(ValidationRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def find_by_id_and_scenario(self, rule_id: UUID, scenario_id: UUID) -> Optional[ValidationRule]:
        result = await self.db.execute(
            select(ValidationRule).where(
                ValidationRule.id == rule_id,
                ValidationRule.scenario_id == scenario_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> ValidationRule:
        rule = ValidationRule(**data)
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def update(self, rule: ValidationRule, data: dict) -> ValidationRule:
        for key, value in data.items():
            setattr(rule, key, value)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def delete(self, rule: ValidationRule) -> None:
        await self.db.delete(rule)
        await self.db.flush()


class ExecutionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_scenario(self, scenario_id: UUID) -> List[TestExecution]:
        result = await self.db.execute(
            select(TestExecution)
            .where(TestExecution.scenario_id == scenario_id)
            .order_by(desc(TestExecution.created_at))
        )
        return list(result.scalars().all())

    async def find_by_id(self, execution_id: UUID) -> Optional[TestExecution]:
        result = await self.db.execute(
            select(TestExecution).where(TestExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def find_by_id_and_scenario(self, execution_id: UUID, scenario_id: UUID) -> Optional[TestExecution]:
        result = await self.db.execute(
            select(TestExecution).where(
                TestExecution.id == execution_id,
                TestExecution.scenario_id == scenario_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> TestExecution:
        execution = TestExecution(**data)
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def update(self, execution: TestExecution, data: dict) -> TestExecution:
        for key, value in data.items():
            setattr(execution, key, value)
        await self.db.flush()
        await self.db.refresh(execution)
        return execution


class ResultRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_execution(self, execution_id: UUID) -> List[TestResult]:
        result = await self.db.execute(
            select(TestResult)
            .where(TestResult.execution_id == execution_id)
            .order_by(asc(TestResult.created_at))
        )
        return list(result.scalars().all())

    async def create(self, data: dict) -> TestResult:
        test_result = TestResult(**data)
        self.db.add(test_result)
        await self.db.flush()
        await self.db.refresh(test_result)
        return test_result

    async def count_by_execution(self, execution_id: UUID) -> Tuple[int, int, int]:
        """Returns (total, passed, failed) counts for an execution."""
        total_result = await self.db.execute(
            select(func.count(TestResult.id)).where(TestResult.execution_id == execution_id)
        )
        total = total_result.scalar_one()

        passed_result = await self.db.execute(
            select(func.count(TestResult.id)).where(
                TestResult.execution_id == execution_id,
                TestResult.passed == True,  # noqa: E712
            )
        )
        passed = passed_result.scalar_one()

        return total, passed, total - passed
