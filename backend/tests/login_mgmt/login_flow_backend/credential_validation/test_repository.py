"""Repository tests for credential validation."""

import uuid

import pytest

from app.login_mgmt.login_flow_backend.credential_validation.models import (
    CredentialValidationDefinition,
    CredentialValidationExecution,
)
from app.login_mgmt.login_flow_backend.credential_validation.repository import (
    CredentialValidationRepository,
)

pytestmark = pytest.mark.asyncio

DEFINITION_DATA = {
    "name": "Repo Test Definition",
    "target_url": "https://example.com/login",
    "version": "1.0",
    "is_active": True,
    "clean_session_required": True,
}


async def _create_definition(db_session) -> CredentialValidationDefinition:
    repo = CredentialValidationRepository(db_session)
    obj = await repo.create_definition(DEFINITION_DATA.copy())
    await db_session.commit()
    await db_session.refresh(obj)
    return obj


class TestDefinitionRepository:
    async def test_create_definition(self, db_session):
        repo = CredentialValidationRepository(db_session)
        obj = await repo.create_definition(DEFINITION_DATA.copy())
        await db_session.commit()
        assert obj.id is not None
        assert obj.name == DEFINITION_DATA["name"]
        assert obj.target_url == DEFINITION_DATA["target_url"]

    async def test_get_definition_found(self, db_session):
        created = await _create_definition(db_session)
        repo = CredentialValidationRepository(db_session)
        fetched = await repo.get_definition(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_definition_not_found(self, db_session):
        repo = CredentialValidationRepository(db_session)
        result = await repo.get_definition(uuid.uuid4())
        assert result is None

    async def test_list_definitions_empty(self, db_session):
        repo = CredentialValidationRepository(db_session)
        items, total = await repo.list_definitions()
        assert items == []
        assert total == 0

    async def test_list_definitions_returns_all(self, db_session):
        repo = CredentialValidationRepository(db_session)
        for i in range(3):
            await repo.create_definition({**DEFINITION_DATA, "name": f"Def {i}"})
        await db_session.commit()
        items, total = await repo.list_definitions()
        assert total == 3
        assert len(items) == 3

    async def test_list_definitions_pagination(self, db_session):
        repo = CredentialValidationRepository(db_session)
        for i in range(5):
            await repo.create_definition({**DEFINITION_DATA, "name": f"Def {i}"})
        await db_session.commit()

        items, total = await repo.list_definitions(page=1, page_size=2)
        assert total == 5
        assert len(items) == 2

    async def test_list_definitions_filter_by_is_active(self, db_session):
        repo = CredentialValidationRepository(db_session)
        await repo.create_definition({**DEFINITION_DATA, "is_active": True})
        await repo.create_definition({**DEFINITION_DATA, "name": "Inactive", "is_active": False})
        await db_session.commit()

        items, total = await repo.list_definitions(filters={"is_active": True})
        assert total == 1
        assert items[0].is_active is True

    async def test_list_definitions_filter_by_name(self, db_session):
        repo = CredentialValidationRepository(db_session)
        await repo.create_definition({**DEFINITION_DATA, "name": "Alpha Test"})
        await repo.create_definition({**DEFINITION_DATA, "name": "Beta Test"})
        await db_session.commit()

        items, total = await repo.list_definitions(filters={"name": "Alpha"})
        assert total == 1
        assert "Alpha" in items[0].name

    async def test_update_definition(self, db_session):
        created = await _create_definition(db_session)
        repo = CredentialValidationRepository(db_session)
        updated = await repo.update_definition(created.id, {"name": "Updated Name"})
        await db_session.commit()
        assert updated is not None
        assert updated.name == "Updated Name"

    async def test_update_definition_not_found(self, db_session):
        repo = CredentialValidationRepository(db_session)
        result = await repo.update_definition(uuid.uuid4(), {"name": "Ghost"})
        assert result is None

    async def test_delete_definition(self, db_session):
        created = await _create_definition(db_session)
        repo = CredentialValidationRepository(db_session)
        deleted = await repo.delete_definition(created.id)
        await db_session.commit()
        assert deleted is True

        fetched = await repo.get_definition(created.id)
        assert fetched is None

    async def test_delete_definition_not_found(self, db_session):
        repo = CredentialValidationRepository(db_session)
        deleted = await repo.delete_definition(uuid.uuid4())
        assert deleted is False


class TestExecutionRepository:
    async def test_create_execution(self, db_session):
        defn = await _create_definition(db_session)
        repo = CredentialValidationRepository(db_session)
        obj = await repo.create_execution(
            {"definition_id": defn.id, "status": "pending"}
        )
        await db_session.commit()
        assert obj.id is not None
        assert obj.definition_id == defn.id
        assert obj.status == "pending"

    async def test_get_execution_found(self, db_session):
        defn = await _create_definition(db_session)
        repo = CredentialValidationRepository(db_session)
        created = await repo.create_execution({"definition_id": defn.id, "status": "pending"})
        await db_session.commit()

        fetched = await repo.get_execution(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_execution_not_found(self, db_session):
        repo = CredentialValidationRepository(db_session)
        result = await repo.get_execution(uuid.uuid4())
        assert result is None

    async def test_list_executions_empty(self, db_session):
        repo = CredentialValidationRepository(db_session)
        items, total = await repo.list_executions()
        assert items == []
        assert total == 0

    async def test_list_executions_filter_by_definition_id(self, db_session):
        defn = await _create_definition(db_session)
        repo = CredentialValidationRepository(db_session)
        await repo.create_execution({"definition_id": defn.id, "status": "pending"})
        await repo.create_execution({"definition_id": defn.id, "status": "running"})
        await db_session.commit()

        items, total = await repo.list_executions(filters={"definition_id": defn.id})
        assert total == 2

    async def test_list_executions_filter_by_status(self, db_session):
        defn = await _create_definition(db_session)
        repo = CredentialValidationRepository(db_session)
        await repo.create_execution({"definition_id": defn.id, "status": "pending"})
        await repo.create_execution({"definition_id": defn.id, "status": "running"})
        await db_session.commit()

        items, total = await repo.list_executions(filters={"status": "pending"})
        assert total == 1

    async def test_update_execution(self, db_session):
        defn = await _create_definition(db_session)
        repo = CredentialValidationRepository(db_session)
        created = await repo.create_execution({"definition_id": defn.id, "status": "pending"})
        await db_session.commit()

        updated = await repo.update_execution(created.id, {"status": "running"})
        await db_session.commit()
        assert updated is not None
        assert updated.status == "running"

    async def test_update_execution_not_found(self, db_session):
        repo = CredentialValidationRepository(db_session)
        result = await repo.update_execution(uuid.uuid4(), {"status": "running"})
        assert result is None
