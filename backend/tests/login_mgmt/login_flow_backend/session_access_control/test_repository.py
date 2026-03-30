"""Repository layer tests for session access control."""

import uuid

import pytest

from app.login_mgmt.login_flow_backend.session_access_control.repository import (
    SessionAccessControlRepository,
)


pytestmark = pytest.mark.asyncio


def _def_data(**kwargs) -> dict:
    base = {
        "name": "Test Definition",
        "target_url": "https://example.com/dashboard",
        "is_active": True,
        "clean_session_required": True,
    }
    base.update(kwargs)
    return base


def _exec_data(definition_id: uuid.UUID, **kwargs) -> dict:
    base = {
        "definition_id": definition_id,
        "status": "pending",
    }
    base.update(kwargs)
    return base


class TestDefinitionRepository:
    async def test_create_and_get_definition(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        obj = await repo.create_definition(_def_data())
        await db_session.commit()

        fetched = await repo.get_definition(obj.id)
        assert fetched is not None
        assert fetched.id == obj.id
        assert fetched.name == "Test Definition"

    async def test_get_definition_not_found(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        result = await repo.get_definition(uuid.uuid4())
        assert result is None

    async def test_list_definitions_empty(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        items, total = await repo.list_definitions()
        assert total == 0
        assert items == []

    async def test_list_definitions_returns_all(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_definition(_def_data(name="Def A"))
        await repo.create_definition(_def_data(name="Def B"))
        await db_session.commit()

        items, total = await repo.list_definitions()
        assert total == 2
        assert len(items) == 2

    async def test_list_definitions_filter_is_active(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_definition(_def_data(name="Active", is_active=True))
        await repo.create_definition(_def_data(name="Inactive", is_active=False))
        await db_session.commit()

        items, total = await repo.list_definitions(filters={"is_active": True})
        assert total == 1
        assert items[0].name == "Active"

    async def test_list_definitions_filter_name(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_definition(_def_data(name="Session Dashboard Test"))
        await repo.create_definition(_def_data(name="Other Test"))
        await db_session.commit()

        items, total = await repo.list_definitions(filters={"name": "Session"})
        assert total == 1
        assert "Session" in items[0].name

    async def test_list_definitions_pagination(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        for i in range(5):
            await repo.create_definition(_def_data(name=f"Def {i}"))
        await db_session.commit()

        items, total = await repo.list_definitions(page=1, page_size=2)
        assert total == 5
        assert len(items) == 2

        items2, _ = await repo.list_definitions(page=2, page_size=2)
        assert len(items2) == 2
        assert items2[0].id != items[0].id

    async def test_list_definitions_sort_asc(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_definition(_def_data(name="Z First"))
        await repo.create_definition(_def_data(name="A First"))
        await db_session.commit()

        items, _ = await repo.list_definitions(sort_by="name", sort_dir="asc")
        assert items[0].name == "A First"

    async def test_update_definition(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        obj = await repo.create_definition(_def_data())
        await db_session.commit()

        updated = await repo.update_definition(obj.id, {"name": "Updated Name"})
        await db_session.commit()
        assert updated is not None
        assert updated.name == "Updated Name"

    async def test_update_definition_not_found(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        result = await repo.update_definition(uuid.uuid4(), {"name": "X"})
        assert result is None

    async def test_delete_definition(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        obj = await repo.create_definition(_def_data())
        await db_session.commit()

        deleted = await repo.delete_definition(obj.id)
        await db_session.commit()
        assert deleted is True

        fetched = await repo.get_definition(obj.id)
        assert fetched is None

    async def test_delete_definition_not_found(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        result = await repo.delete_definition(uuid.uuid4())
        assert result is False


class TestExecutionRepository:
    async def _create_definition(self, db_session) -> uuid.UUID:
        repo = SessionAccessControlRepository(db_session)
        obj = await repo.create_definition(_def_data())
        await db_session.commit()
        return obj.id

    async def test_create_and_get_execution(self, db_session):
        def_id = await self._create_definition(db_session)
        repo = SessionAccessControlRepository(db_session)
        obj = await repo.create_execution(_exec_data(def_id))
        await db_session.commit()

        fetched = await repo.get_execution(obj.id)
        assert fetched is not None
        assert fetched.id == obj.id
        assert fetched.definition_id == def_id

    async def test_get_execution_not_found(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        result = await repo.get_execution(uuid.uuid4())
        assert result is None

    async def test_list_executions_filter_by_definition_id(self, db_session):
        def_id = await self._create_definition(db_session)
        repo = SessionAccessControlRepository(db_session)
        await repo.create_execution(_exec_data(def_id))
        await repo.create_execution(_exec_data(def_id))
        await db_session.commit()

        items, total = await repo.list_executions(filters={"definition_id": def_id})
        assert total == 2

    async def test_list_executions_filter_by_status(self, db_session):
        def_id = await self._create_definition(db_session)
        repo = SessionAccessControlRepository(db_session)
        await repo.create_execution(_exec_data(def_id, status="pending"))
        await repo.create_execution(_exec_data(def_id, status="running"))
        await db_session.commit()

        items, total = await repo.list_executions(filters={"status": "pending"})
        assert total == 1
        assert items[0].status.value == "pending"

    async def test_list_executions_filter_by_session_state(self, db_session):
        def_id = await self._create_definition(db_session)
        repo = SessionAccessControlRepository(db_session)
        await repo.create_execution(_exec_data(def_id, session_state="authenticated"))
        await repo.create_execution(_exec_data(def_id, session_state="guest"))
        await db_session.commit()

        items, total = await repo.list_executions(filters={"session_state": "authenticated"})
        assert total == 1

    async def test_list_executions_pagination(self, db_session):
        def_id = await self._create_definition(db_session)
        repo = SessionAccessControlRepository(db_session)
        for _ in range(4):
            await repo.create_execution(_exec_data(def_id))
        await db_session.commit()

        items, total = await repo.list_executions(page=1, page_size=2)
        assert total == 4
        assert len(items) == 2

    async def test_update_execution(self, db_session):
        def_id = await self._create_definition(db_session)
        repo = SessionAccessControlRepository(db_session)
        obj = await repo.create_execution(_exec_data(def_id))
        await db_session.commit()

        updated = await repo.update_execution(obj.id, {"status": "running"})
        await db_session.commit()
        assert updated is not None
        assert updated.status.value == "running"

    async def test_update_execution_not_found(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        result = await repo.update_execution(uuid.uuid4(), {"status": "running"})
        assert result is None
