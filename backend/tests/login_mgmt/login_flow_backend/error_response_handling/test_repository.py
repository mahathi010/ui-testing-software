"""Repository-layer tests for error response handling."""

import uuid

import pytest

from app.login_mgmt.login_flow_backend.error_response_handling.repository import (
    ErrorResponseDefinitionRepository,
    ErrorResponseExecutionRepository,
)

pytestmark = pytest.mark.asyncio

_DEF_DATA = {
    "name": "Repo Test Definition",
    "target_url": "https://example.com/error-page",
    "version": "1.0",
    "is_active": True,
}


class TestDefinitionRepository:
    async def test_find_by_id_returns_none_for_missing(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        result = await repo.find_by_id(uuid.uuid4())
        assert result is None

    async def test_create_persists_record(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        obj = await repo.create(_DEF_DATA)
        assert obj.id is not None
        assert obj.name == _DEF_DATA["name"]
        assert obj.target_url == _DEF_DATA["target_url"]

    async def test_find_by_id_returns_created(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        created = await repo.create(_DEF_DATA)
        fetched = await repo.find_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_find_all_empty(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        items, total = await repo.find_all()
        assert items == []
        assert total == 0

    async def test_find_all_pagination(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        for i in range(5):
            await repo.create({**_DEF_DATA, "name": f"Definition {i}"})

        items, total = await repo.find_all(page=1, page_size=2)
        assert total == 5
        assert len(items) == 2

    async def test_find_all_filter_by_is_active(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        await repo.create({**_DEF_DATA, "is_active": True})
        await repo.create({**_DEF_DATA, "name": "Inactive", "is_active": False})

        active_items, active_total = await repo.find_all(filters={"is_active": True})
        assert active_total == 1

        inactive_items, inactive_total = await repo.find_all(filters={"is_active": False})
        assert inactive_total == 1

    async def test_update_changes_fields(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        created = await repo.create(_DEF_DATA)
        updated = await repo.update(created.id, {"name": "Updated Name"})
        assert updated is not None
        assert updated.name == "Updated Name"

    async def test_update_returns_none_for_missing(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        result = await repo.update(uuid.uuid4(), {"name": "Ghost"})
        assert result is None

    async def test_delete_removes_record(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        created = await repo.create(_DEF_DATA)
        deleted = await repo.delete(created.id)
        assert deleted is True
        fetched = await repo.find_by_id(created.id)
        assert fetched is None

    async def test_delete_returns_false_for_missing(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        result = await repo.delete(uuid.uuid4())
        assert result is False


class TestExecutionRepository:
    async def _create_definition(self, db_session):
        repo = ErrorResponseDefinitionRepository(db_session)
        return await repo.create(_DEF_DATA)

    async def test_find_by_id_returns_none_for_missing(self, db_session):
        repo = ErrorResponseExecutionRepository(db_session)
        result = await repo.find_by_id(uuid.uuid4())
        assert result is None

    async def test_create_execution_persists(self, db_session):
        defn = await self._create_definition(db_session)
        repo = ErrorResponseExecutionRepository(db_session)
        obj = await repo.create({"definition_id": defn.id, "status": "pending"})
        assert obj.id is not None
        assert obj.definition_id == defn.id
        assert obj.status.value == "pending"

    async def test_find_all_returns_paginated(self, db_session):
        defn = await self._create_definition(db_session)
        repo = ErrorResponseExecutionRepository(db_session)
        for _ in range(3):
            await repo.create({"definition_id": defn.id, "status": "pending"})

        items, total = await repo.find_all(page=1, page_size=2)
        assert total == 3
        assert len(items) == 2

    async def test_find_all_filter_by_definition_id(self, db_session):
        defn = await self._create_definition(db_session)
        repo = ErrorResponseExecutionRepository(db_session)
        await repo.create({"definition_id": defn.id, "status": "pending"})

        items, total = await repo.find_all(filters={"definition_id": defn.id})
        assert total == 1

        items_other, total_other = await repo.find_all(filters={"definition_id": uuid.uuid4()})
        assert total_other == 0

    async def test_update_execution(self, db_session):
        defn = await self._create_definition(db_session)
        repo = ErrorResponseExecutionRepository(db_session)
        created = await repo.create({"definition_id": defn.id, "status": "pending"})
        updated = await repo.update(created.id, {"status": "running"})
        assert updated is not None
        assert updated.status == "running"
