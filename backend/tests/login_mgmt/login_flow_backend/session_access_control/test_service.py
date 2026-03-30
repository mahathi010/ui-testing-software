"""Service layer tests for session access control."""

import uuid

import pytest
from fastapi import HTTPException

from app.login_mgmt.login_flow_backend.session_access_control.schema import (
    DefinitionCreate,
    DefinitionUpdate,
    ExecutionCreate,
    ExecutionUpdate,
    ExecutionStatusEnum,
)
from app.login_mgmt.login_flow_backend.session_access_control.service import (
    SessionAccessControlService,
    _build_default_requirements,
)


pytestmark = pytest.mark.asyncio


class TestDefaultRequirements:
    def test_returns_30_requirements(self):
        reqs = _build_default_requirements()
        assert len(reqs) == 30

    def test_fr_ids_are_sequential(self):
        reqs = _build_default_requirements()
        fr_ids = [r["fr_id"] for r in reqs]
        assert "FR-1" in fr_ids
        assert "FR-30" in fr_ids

    def test_all_have_required_fields(self):
        reqs = _build_default_requirements()
        for req in reqs:
            assert "fr_id" in req
            assert "description" in req
            assert "lifecycle_section" in req
            assert "acceptance_signal" in req
            assert "applicability" in req

    def test_lifecycle_sections_covered(self):
        reqs = _build_default_requirements()
        sections = {r["lifecycle_section"] for r in reqs}
        assert "page_access" in sections
        assert "session_initialization" in sections
        assert "guarded_actions" in sections
        assert "protected_navigation" in sections
        assert "session_expiry" in sections
        assert "loading_empty_error" in sections


class TestDefinitionService:
    async def test_create_definition_injects_default_requirements(self, db_session):
        svc = SessionAccessControlService(db_session)
        data = DefinitionCreate(
            name="Session AC Test",
            target_url="https://example.com/dashboard",
        )
        result = await svc.create_definition(data)
        assert result.requirements is not None
        assert len(result.requirements) == 30

    async def test_create_definition_keeps_custom_requirements(self, db_session):
        from app.login_mgmt.login_flow_backend.session_access_control.schema import (
            RequirementSpec,
            ApplicabilityEnum,
        )
        svc = SessionAccessControlService(db_session)
        custom_req = RequirementSpec(
            fr_id="CUSTOM-1",
            description="Custom requirement",
            lifecycle_section="page_access",
            acceptance_signal="Custom signal",
            applicability=ApplicabilityEnum.required,
        )
        data = DefinitionCreate(
            name="Session AC Test Custom",
            target_url="https://example.com/dashboard",
            requirements=[custom_req],
        )
        result = await svc.create_definition(data)
        assert result.requirements is not None
        assert len(result.requirements) == 1
        assert result.requirements[0]["fr_id"] == "CUSTOM-1"

    async def test_get_definition_not_found(self, db_session):
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.get_definition(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_list_definitions_empty(self, db_session):
        svc = SessionAccessControlService(db_session)
        result = await svc.list_definitions()
        assert result.total == 0
        assert result.items == []

    async def test_list_definitions_pagination(self, db_session):
        svc = SessionAccessControlService(db_session)
        for i in range(5):
            await svc.create_definition(
                DefinitionCreate(name=f"Def {i}", target_url="https://example.com")
            )
        result = await svc.list_definitions(page=1, page_size=3)
        assert result.total == 5
        assert len(result.items) == 3

    async def test_list_definitions_filter_is_active(self, db_session):
        svc = SessionAccessControlService(db_session)
        await svc.create_definition(
            DefinitionCreate(name="Active", target_url="https://example.com", is_active=True)
        )
        await svc.create_definition(
            DefinitionCreate(name="Inactive", target_url="https://example.com", is_active=False)
        )
        result = await svc.list_definitions(filters={"is_active": True})
        assert result.total == 1
        assert result.items[0].name == "Active"

    async def test_update_definition(self, db_session):
        svc = SessionAccessControlService(db_session)
        created = await svc.create_definition(
            DefinitionCreate(name="Original", target_url="https://example.com")
        )
        updated = await svc.update_definition(created.id, DefinitionUpdate(name="Updated"))
        assert updated.name == "Updated"

    async def test_update_definition_not_found(self, db_session):
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_definition(uuid.uuid4(), DefinitionUpdate(name="X"))
        assert exc_info.value.status_code == 404

    async def test_delete_definition(self, db_session):
        svc = SessionAccessControlService(db_session)
        created = await svc.create_definition(
            DefinitionCreate(name="To Delete", target_url="https://example.com")
        )
        await svc.delete_definition(created.id)
        with pytest.raises(HTTPException) as exc_info:
            await svc.get_definition(created.id)
        assert exc_info.value.status_code == 404

    async def test_delete_definition_not_found(self, db_session):
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_definition(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_list_definitions_unsupported_filter_raises_422(self, db_session):
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.list_definitions(filters={"unsupported_field": "value"})
        assert exc_info.value.status_code == 422


class TestExecutionService:
    async def _create_definition(self, db_session):
        svc = SessionAccessControlService(db_session)
        return await svc.create_definition(
            DefinitionCreate(name="Exec Test Def", target_url="https://example.com")
        )

    async def test_create_execution(self, db_session):
        defn = await self._create_definition(db_session)
        svc = SessionAccessControlService(db_session)
        result = await svc.create_execution(
            ExecutionCreate(definition_id=defn.id, session_state="authenticated")
        )
        assert result.definition_id == defn.id
        assert result.status == ExecutionStatusEnum.pending
        assert str(result.session_state) == "authenticated"

    async def test_create_execution_definition_not_found(self, db_session):
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.create_execution(
                ExecutionCreate(definition_id=uuid.uuid4())
            )
        assert exc_info.value.status_code == 404

    async def test_get_execution_not_found(self, db_session):
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.get_execution(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_valid_status_transitions(self, db_session):
        defn = await self._create_definition(db_session)
        svc = SessionAccessControlService(db_session)
        exec_ = await svc.create_execution(ExecutionCreate(definition_id=defn.id))
        assert exec_.status == ExecutionStatusEnum.pending

        running = await svc.update_execution(exec_.id, ExecutionUpdate(status=ExecutionStatusEnum.running))
        assert running.status == ExecutionStatusEnum.running

        passed = await svc.update_execution(exec_.id, ExecutionUpdate(status=ExecutionStatusEnum.passed))
        assert passed.status == ExecutionStatusEnum.passed

    async def test_invalid_status_transition_raises_422(self, db_session):
        defn = await self._create_definition(db_session)
        svc = SessionAccessControlService(db_session)
        exec_ = await svc.create_execution(ExecutionCreate(definition_id=defn.id))

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_execution(exec_.id, ExecutionUpdate(status=ExecutionStatusEnum.passed))
        assert exc_info.value.status_code == 422

    async def test_failed_to_pending_transition(self, db_session):
        defn = await self._create_definition(db_session)
        svc = SessionAccessControlService(db_session)
        exec_ = await svc.create_execution(ExecutionCreate(definition_id=defn.id))
        await svc.update_execution(exec_.id, ExecutionUpdate(status=ExecutionStatusEnum.running))
        await svc.update_execution(exec_.id, ExecutionUpdate(status=ExecutionStatusEnum.failed))
        result = await svc.update_execution(exec_.id, ExecutionUpdate(status=ExecutionStatusEnum.pending))
        assert result.status == ExecutionStatusEnum.pending

    async def test_list_executions_filter_by_definition_id(self, db_session):
        defn = await self._create_definition(db_session)
        svc = SessionAccessControlService(db_session)
        await svc.create_execution(ExecutionCreate(definition_id=defn.id))
        await svc.create_execution(ExecutionCreate(definition_id=defn.id))

        result = await svc.list_executions(filters={"definition_id": defn.id})
        assert result.total == 2

    async def test_list_executions_filter_by_session_state(self, db_session):
        defn = await self._create_definition(db_session)
        svc = SessionAccessControlService(db_session)
        await svc.create_execution(
            ExecutionCreate(definition_id=defn.id, session_state="authenticated")
        )
        await svc.create_execution(
            ExecutionCreate(definition_id=defn.id, session_state="guest")
        )

        result = await svc.list_executions(filters={"session_state": "authenticated"})
        assert result.total == 1

    async def test_list_executions_unsupported_filter_raises_422(self, db_session):
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.list_executions(filters={"bad_field": "value"})
        assert exc_info.value.status_code == 422
