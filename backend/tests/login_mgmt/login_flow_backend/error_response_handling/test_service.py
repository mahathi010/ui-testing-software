"""Service tests for error response handling (real DB via db_session fixture)."""

import uuid

import pytest
from fastapi import HTTPException

from app.login_mgmt.login_flow_backend.error_response_handling.schema import (
    ErrorResponseDefinitionCreate,
    ErrorResponseDefinitionUpdate,
    ErrorResponseExecutionCreate,
    ErrorResponseExecutionUpdate,
    ExecutionStatusEnum,
)
from app.login_mgmt.login_flow_backend.error_response_handling.service import (
    ErrorResponseDefinitionService,
    ErrorResponseExecutionService,
)

pytestmark = pytest.mark.asyncio

_DEF_CREATE = ErrorResponseDefinitionCreate(
    name="Service Test Definition",
    target_url="https://example.com/error-page",
    version="1.0",
    is_active=True,
)


class TestDefinitionService:
    async def test_create_definition_succeeds(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        result = await svc.create_definition(_DEF_CREATE)
        assert result.id is not None
        assert result.name == _DEF_CREATE.name
        assert result.target_url == _DEF_CREATE.target_url

    async def test_create_definition_injects_24_requirements(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        result = await svc.create_definition(_DEF_CREATE)
        assert isinstance(result.requirements, list)
        assert len(result.requirements) == 24

    async def test_create_definition_keeps_custom_requirements(self, db_session):
        custom_reqs = [{"fr_id": "CUSTOM-1", "description": "Custom"}]
        payload = ErrorResponseDefinitionCreate(
            name="Custom Reqs",
            target_url="https://example.com/error-page",
            requirements=custom_reqs,
        )
        svc = ErrorResponseDefinitionService(db_session)
        result = await svc.create_definition(payload)
        assert len(result.requirements) == 1
        assert result.requirements[0]["fr_id"] == "CUSTOM-1"

    async def test_get_definition_found(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        created = await svc.create_definition(_DEF_CREATE)
        fetched = await svc.get_definition(created.id)
        assert fetched.id == created.id

    async def test_get_definition_not_found_raises_404(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.get_definition(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_list_definitions_returns_all(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        for i in range(3):
            await svc.create_definition(
                ErrorResponseDefinitionCreate(name=f"Def {i}", target_url="https://example.com/error-page")
            )
        result = await svc.list_definitions()
        assert result.total == 3
        assert len(result.items) == 3

    async def test_list_definitions_pagination(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        for i in range(5):
            await svc.create_definition(
                ErrorResponseDefinitionCreate(name=f"Def {i}", target_url="https://example.com/error-page")
            )
        result = await svc.list_definitions(page=1, page_size=2)
        assert result.total == 5
        assert len(result.items) == 2
        assert result.page == 1
        assert result.page_size == 2

    async def test_list_definitions_unsupported_filter_raises_422(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.list_definitions(filters={"unknown_field": "value"})
        assert exc_info.value.status_code == 422

    async def test_update_definition_succeeds(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        created = await svc.create_definition(_DEF_CREATE)
        updated = await svc.update_definition(created.id, ErrorResponseDefinitionUpdate(name="New Name"))
        assert updated.name == "New Name"

    async def test_update_definition_not_found_raises_404(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_definition(uuid.uuid4(), ErrorResponseDefinitionUpdate(name="Ghost"))
        assert exc_info.value.status_code == 404

    async def test_delete_definition_succeeds(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        created = await svc.create_definition(_DEF_CREATE)
        await svc.delete_definition(created.id)
        with pytest.raises(HTTPException):
            await svc.get_definition(created.id)

    async def test_delete_definition_not_found_raises_404(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_definition(uuid.uuid4())
        assert exc_info.value.status_code == 404


class TestExecutionService:
    async def _create_definition(self, db_session):
        svc = ErrorResponseDefinitionService(db_session)
        return await svc.create_definition(_DEF_CREATE)

    async def test_create_execution_succeeds(self, db_session):
        defn = await self._create_definition(db_session)
        svc = ErrorResponseExecutionService(db_session)
        result = await svc.create_execution(
            ErrorResponseExecutionCreate(definition_id=defn.id)
        )
        assert result.id is not None
        assert result.definition_id == defn.id
        assert result.status == "pending"

    async def test_create_execution_definition_not_found_raises_404(self, db_session):
        svc = ErrorResponseExecutionService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.create_execution(ErrorResponseExecutionCreate(definition_id=uuid.uuid4()))
        assert exc_info.value.status_code == 404

    async def test_get_execution_found(self, db_session):
        defn = await self._create_definition(db_session)
        svc = ErrorResponseExecutionService(db_session)
        created = await svc.create_execution(ErrorResponseExecutionCreate(definition_id=defn.id))
        fetched = await svc.get_execution(created.id)
        assert fetched.id == created.id

    async def test_get_execution_not_found_raises_404(self, db_session):
        svc = ErrorResponseExecutionService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.get_execution(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_list_executions_unsupported_filter_raises_422(self, db_session):
        svc = ErrorResponseExecutionService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.list_executions(filters={"bad_filter": "x"})
        assert exc_info.value.status_code == 422

    async def test_update_execution_valid_transition(self, db_session):
        defn = await self._create_definition(db_session)
        svc = ErrorResponseExecutionService(db_session)
        created = await svc.create_execution(ErrorResponseExecutionCreate(definition_id=defn.id))
        updated = await svc.update_execution(
            created.id, ErrorResponseExecutionUpdate(status=ExecutionStatusEnum.running)
        )
        assert updated.status == "running"

    async def test_update_execution_invalid_transition_raises_422(self, db_session):
        defn = await self._create_definition(db_session)
        svc = ErrorResponseExecutionService(db_session)
        created = await svc.create_execution(ErrorResponseExecutionCreate(definition_id=defn.id))
        with pytest.raises(HTTPException) as exc_info:
            # pending → passed is not valid
            await svc.update_execution(
                created.id, ErrorResponseExecutionUpdate(status=ExecutionStatusEnum.passed)
            )
        assert exc_info.value.status_code == 422

    async def test_update_execution_full_lifecycle(self, db_session):
        defn = await self._create_definition(db_session)
        svc = ErrorResponseExecutionService(db_session)
        created = await svc.create_execution(ErrorResponseExecutionCreate(definition_id=defn.id))

        # pending → running
        ex = await svc.update_execution(
            created.id, ErrorResponseExecutionUpdate(status=ExecutionStatusEnum.running)
        )
        assert ex.status == "running"

        # running → passed
        ex = await svc.update_execution(
            created.id, ErrorResponseExecutionUpdate(status=ExecutionStatusEnum.passed)
        )
        assert ex.status == "passed"

    async def test_update_execution_not_found_raises_404(self, db_session):
        svc = ErrorResponseExecutionService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_execution(
                uuid.uuid4(), ErrorResponseExecutionUpdate(status=ExecutionStatusEnum.running)
            )
        assert exc_info.value.status_code == 404
