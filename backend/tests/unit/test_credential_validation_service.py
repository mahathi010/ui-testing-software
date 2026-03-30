"""Unit tests for CredentialValidationService."""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.login_mgmt.login_flow_backend.credential_validation.models import (  # noqa: F401
    CredentialValidationScenario,
    CoverageArea,
    ExecutionStatus,
    RuleType,
    TestExecution,
    TestResult,
    ValidationRule,
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
from app.login_mgmt.login_flow_backend.credential_validation.service import (
    CredentialValidationService,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def svc(db_session):
    return CredentialValidationService(db_session)


# ── Helper factories ──────────────────────────────────────────────────────────

def make_scenario_data(**kwargs):
    defaults = {
        "page_url": "https://aitube.staging.logicpatterns.ai/",
        "name": "Login Page Rendering",
        "description": "Validates page loads correctly",
        "coverage_area": CoverageArea.RENDERING,
        "requirement_ref": "FR-1",
        "is_active": True,
    }
    defaults.update(kwargs)
    return ScenarioCreate(**defaults)


def make_rule_data(**kwargs):
    defaults = {
        "rule_type": RuleType.PAGE_TITLE,
        "selector": "title",
        "expected_value": "AITube",
        "description": "Page title check",
    }
    defaults.update(kwargs)
    return RuleCreate(**defaults)


# ── Scenario CRUD ─────────────────────────────────────────────────────────────

async def test_create_scenario_happy_path(svc):
    data = make_scenario_data()
    scenario = await svc.create_scenario(data)
    assert scenario.id is not None
    assert scenario.name == "Login Page Rendering"
    assert scenario.coverage_area == CoverageArea.RENDERING
    assert scenario.is_active is True


async def test_get_scenario_found(svc):
    created = await svc.create_scenario(make_scenario_data())
    fetched = await svc.get_scenario(created.id)
    assert fetched.id == created.id
    assert fetched.name == created.name


async def test_get_scenario_not_found(svc):
    import uuid
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_scenario(uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_update_scenario(svc):
    created = await svc.create_scenario(make_scenario_data())
    updated = await svc.update_scenario(
        created.id,
        ScenarioUpdate(name="Updated Name", is_active=False),
    )
    assert updated.name == "Updated Name"
    assert updated.is_active is False
    assert updated.coverage_area == CoverageArea.RENDERING  # unchanged


async def test_update_scenario_not_found(svc):
    import uuid
    with pytest.raises(HTTPException) as exc_info:
        await svc.update_scenario(uuid.uuid4(), ScenarioUpdate(name="x"))
    assert exc_info.value.status_code == 404


async def test_delete_scenario(svc):
    created = await svc.create_scenario(make_scenario_data())
    await svc.delete_scenario(created.id)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_scenario(created.id)
    assert exc_info.value.status_code == 404


async def test_list_scenarios_pagination(svc):
    for i in range(5):
        await svc.create_scenario(make_scenario_data(name=f"Scenario {i}"))

    filters = ScenarioFilterParams(page=1, page_size=3)
    items, total, pages = await svc.list_scenarios(filters)
    assert total == 5
    assert len(items) == 3
    assert pages == 2

    filters2 = ScenarioFilterParams(page=2, page_size=3)
    items2, total2, pages2 = await svc.list_scenarios(filters2)
    assert len(items2) == 2
    assert total2 == 5


async def test_list_scenarios_filter_by_coverage_area(svc):
    await svc.create_scenario(make_scenario_data(coverage_area=CoverageArea.RENDERING))
    await svc.create_scenario(make_scenario_data(coverage_area=CoverageArea.NAVIGATION, name="Nav Test"))

    filters = ScenarioFilterParams(coverage_area=CoverageArea.RENDERING)
    items, total, _ = await svc.list_scenarios(filters)
    assert total == 1
    assert items[0].coverage_area == CoverageArea.RENDERING


async def test_list_scenarios_filter_by_is_active(svc):
    await svc.create_scenario(make_scenario_data(is_active=True))
    await svc.create_scenario(make_scenario_data(is_active=False, name="Inactive"))

    filters = ScenarioFilterParams(is_active=False)
    items, total, _ = await svc.list_scenarios(filters)
    assert total == 1
    assert items[0].is_active is False


async def test_list_scenarios_filter_by_requirement_ref(svc):
    await svc.create_scenario(make_scenario_data(requirement_ref="FR-1"))
    await svc.create_scenario(make_scenario_data(requirement_ref="FR-5", name="FR5 test"))

    filters = ScenarioFilterParams(requirement_ref="FR-1")
    items, total, _ = await svc.list_scenarios(filters)
    assert total == 1
    assert items[0].requirement_ref == "FR-1"


# ── Rule CRUD ─────────────────────────────────────────────────────────────────

async def test_create_rule(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    rule = await svc.create_rule(scenario.id, make_rule_data())
    assert rule.id is not None
    assert rule.scenario_id == scenario.id
    assert rule.rule_type == RuleType.PAGE_TITLE


async def test_get_rule_found(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    created = await svc.create_rule(scenario.id, make_rule_data())
    fetched = await svc.get_rule(scenario.id, created.id)
    assert fetched.id == created.id


async def test_get_rule_not_found(svc):
    import uuid
    scenario = await svc.create_scenario(make_scenario_data())
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_rule(scenario.id, uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_get_rule_wrong_scenario(svc):
    """Rule belonging to different scenario should not be found."""
    import uuid
    scenario1 = await svc.create_scenario(make_scenario_data())
    scenario2 = await svc.create_scenario(make_scenario_data(name="Scenario 2"))
    rule = await svc.create_rule(scenario1.id, make_rule_data())

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_rule(scenario2.id, rule.id)
    assert exc_info.value.status_code == 404


async def test_update_rule(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    rule = await svc.create_rule(scenario.id, make_rule_data())
    updated = await svc.update_rule(scenario.id, rule.id, RuleUpdate(expected_value="NewTitle"))
    assert updated.expected_value == "NewTitle"
    assert updated.rule_type == RuleType.PAGE_TITLE  # unchanged


async def test_delete_rule(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    rule = await svc.create_rule(scenario.id, make_rule_data())
    await svc.delete_rule(scenario.id, rule.id)
    with pytest.raises(HTTPException):
        await svc.get_rule(scenario.id, rule.id)


async def test_list_rules(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    await svc.create_rule(scenario.id, make_rule_data(rule_type=RuleType.PAGE_TITLE))
    await svc.create_rule(scenario.id, make_rule_data(rule_type=RuleType.ELEMENT_VISIBLE, selector="#login-btn"))

    rules = await svc.list_rules(scenario.id)
    assert len(rules) == 2


async def test_list_rules_wrong_scenario(svc):
    import uuid
    with pytest.raises(HTTPException) as exc_info:
        await svc.list_rules(uuid.uuid4())
    assert exc_info.value.status_code == 404


# ── Execution CRUD ────────────────────────────────────────────────────────────

async def test_create_execution(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    execution = await svc.create_execution(scenario.id)
    assert execution.id is not None
    assert execution.scenario_id == scenario.id
    assert execution.status == ExecutionStatus.PENDING


async def test_create_execution_invalid_scenario(svc):
    import uuid
    with pytest.raises(HTTPException) as exc_info:
        await svc.create_execution(uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_update_execution_status_to_running(svc):
    from datetime import datetime, timezone
    scenario = await svc.create_scenario(make_scenario_data())
    execution = await svc.create_execution(scenario.id)

    now = datetime.now(timezone.utc)
    updated = await svc.update_execution_status(
        scenario.id,
        execution.id,
        ExecutionStatusUpdate(status=ExecutionStatus.RUNNING, started_at=now),
    )
    assert updated.status == ExecutionStatus.RUNNING
    assert updated.started_at is not None


async def test_update_execution_status_to_passed(svc):
    from datetime import datetime, timezone
    scenario = await svc.create_scenario(make_scenario_data())
    execution = await svc.create_execution(scenario.id)

    now = datetime.now(timezone.utc)
    updated = await svc.update_execution_status(
        scenario.id,
        execution.id,
        ExecutionStatusUpdate(
            status=ExecutionStatus.PASSED,
            completed_at=now,
            total_rules=3,
            passed_rules=3,
            failed_rules=0,
        ),
    )
    assert updated.status == ExecutionStatus.PASSED
    assert updated.total_rules == 3
    assert updated.passed_rules == 3


async def test_update_execution_status_to_failed(svc):
    from datetime import datetime, timezone
    scenario = await svc.create_scenario(make_scenario_data())
    execution = await svc.create_execution(scenario.id)

    now = datetime.now(timezone.utc)
    updated = await svc.update_execution_status(
        scenario.id,
        execution.id,
        ExecutionStatusUpdate(
            status=ExecutionStatus.FAILED,
            completed_at=now,
            total_rules=3,
            passed_rules=1,
            failed_rules=2,
        ),
    )
    assert updated.status == ExecutionStatus.FAILED
    assert updated.failed_rules == 2


async def test_get_execution_not_found(svc):
    import uuid
    scenario = await svc.create_scenario(make_scenario_data())
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_execution(scenario.id, uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_list_executions(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    await svc.create_execution(scenario.id)
    await svc.create_execution(scenario.id)

    executions = await svc.list_executions(scenario.id)
    assert len(executions) == 2


# ── Results ───────────────────────────────────────────────────────────────────

async def test_record_result_passed(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    rule = await svc.create_rule(scenario.id, make_rule_data())
    execution = await svc.create_execution(scenario.id)

    result = await svc.record_result(
        scenario.id,
        execution.id,
        ResultCreate(rule_id=rule.id, passed=True, actual_value="AITube"),
    )
    assert result.passed is True
    assert result.actual_value == "AITube"
    assert result.execution_id == execution.id
    assert result.rule_id == rule.id


async def test_record_result_failed(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    rule = await svc.create_rule(scenario.id, make_rule_data())
    execution = await svc.create_execution(scenario.id)

    result = await svc.record_result(
        scenario.id,
        execution.id,
        ResultCreate(rule_id=rule.id, passed=False, error_message="Element not found"),
    )
    assert result.passed is False
    assert result.error_message == "Element not found"


async def test_record_result_rule_not_in_scenario(svc):
    import uuid
    scenario = await svc.create_scenario(make_scenario_data())
    execution = await svc.create_execution(scenario.id)

    with pytest.raises(HTTPException) as exc_info:
        await svc.record_result(
            scenario.id,
            execution.id,
            ResultCreate(rule_id=uuid.uuid4(), passed=True),
        )
    assert exc_info.value.status_code == 404


async def test_list_results(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    rule1 = await svc.create_rule(scenario.id, make_rule_data())
    rule2 = await svc.create_rule(scenario.id, make_rule_data(rule_type=RuleType.ELEMENT_VISIBLE, selector="#btn"))
    execution = await svc.create_execution(scenario.id)

    await svc.record_result(scenario.id, execution.id, ResultCreate(rule_id=rule1.id, passed=True))
    await svc.record_result(scenario.id, execution.id, ResultCreate(rule_id=rule2.id, passed=False))

    results = await svc.list_results(scenario.id, execution.id)
    assert len(results) == 2


# ── Execution summary ─────────────────────────────────────────────────────────

async def test_execution_summary(svc):
    scenario = await svc.create_scenario(make_scenario_data())
    rule1 = await svc.create_rule(scenario.id, make_rule_data())
    rule2 = await svc.create_rule(scenario.id, make_rule_data(rule_type=RuleType.ELEMENT_VISIBLE, selector="#btn"))
    rule3 = await svc.create_rule(scenario.id, make_rule_data(rule_type=RuleType.AUTH_GATE, selector="#auth"))
    execution = await svc.create_execution(scenario.id)

    await svc.record_result(scenario.id, execution.id, ResultCreate(rule_id=rule1.id, passed=True))
    await svc.record_result(scenario.id, execution.id, ResultCreate(rule_id=rule2.id, passed=True))
    await svc.record_result(scenario.id, execution.id, ResultCreate(rule_id=rule3.id, passed=False))

    summary = await svc.get_execution_summary(scenario.id, execution.id)
    assert summary["total_rules"] == 3
    assert summary["passed_rules"] == 2
    assert summary["failed_rules"] == 1
    assert abs(summary["pass_rate"] - 66.666) < 0.1


async def test_execution_summary_empty(svc):
    """Summary with no results should have 0 pass rate."""
    scenario = await svc.create_scenario(make_scenario_data())
    execution = await svc.create_execution(scenario.id)

    summary = await svc.get_execution_summary(scenario.id, execution.id)
    assert summary["total_rules"] == 0
    assert summary["pass_rate"] == 0.0


# ── Coverage area completeness ────────────────────────────────────────────────

async def test_all_coverage_areas_can_be_created(svc):
    """All five coverage areas should be storable."""
    for area in CoverageArea:
        scenario = await svc.create_scenario(make_scenario_data(coverage_area=area, name=f"Test {area.value}"))
        assert scenario.coverage_area == area


async def test_all_rule_types_can_be_created(svc):
    """All nine rule types should be storable."""
    scenario = await svc.create_scenario(make_scenario_data())
    for rt in RuleType:
        rule = await svc.create_rule(scenario.id, make_rule_data(rule_type=rt, selector=f"#{rt.value}"))
        assert rule.rule_type == rt


async def test_all_execution_statuses_can_be_set(svc):
    """All execution statuses should be settable."""
    scenario = await svc.create_scenario(make_scenario_data())
    for st in ExecutionStatus:
        execution = await svc.create_execution(scenario.id)
        updated = await svc.update_execution_status(
            scenario.id, execution.id, ExecutionStatusUpdate(status=st)
        )
        assert updated.status == st
