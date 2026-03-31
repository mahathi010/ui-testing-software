"""Repository tests for session access control."""

import uuid

import pytest

from app.login_mgmt.login_flow_backend.session_access_control.repository import (
    SessionAccessControlRepository,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def resource_data():
    return {
        "resource_path": "/protected/page",
        "resource_name": "Protected Page",
        "protection_level": "authenticated",
        "description": "A test protected resource",
        "is_active": True,
    }


@pytest.fixture
def record_data():
    return {
        "session_token": "valid_user_123",
        "session_status": "active",
        "action_type": "page_view",
        "outcome": "allowed",
    }


class TestResourceRepository:
    async def test_create_resource(self, db_session, resource_data):
        repo = SessionAccessControlRepository(db_session)
        obj = await repo.create_resource(resource_data)
        await db_session.commit()
        assert obj.id is not None
        assert obj.resource_path == resource_data["resource_path"]
        assert obj.resource_name == resource_data["resource_name"]
        assert obj.protection_level.value == "authenticated"

    async def test_get_resource(self, db_session, resource_data):
        repo = SessionAccessControlRepository(db_session)
        created = await repo.create_resource(resource_data)
        await db_session.commit()

        fetched = await repo.get_resource(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_resource_not_found(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        result = await repo.get_resource(uuid.uuid4())
        assert result is None

    async def test_get_resource_by_path(self, db_session, resource_data):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_resource(resource_data)
        await db_session.commit()

        result = await repo.get_resource_by_path("/protected/page")
        assert result is not None
        assert result.resource_path == "/protected/page"

    async def test_get_resource_by_path_not_found(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        result = await repo.get_resource_by_path("/nonexistent")
        assert result is None

    async def test_list_resources_empty(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        items, total = await repo.list_resources()
        assert items == []
        assert total == 0

    async def test_list_resources_returns_created(self, db_session, resource_data):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_resource(resource_data)
        await db_session.commit()

        items, total = await repo.list_resources()
        assert total == 1
        assert len(items) == 1

    async def test_list_resources_filter_by_is_active(self, db_session, resource_data):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_resource(resource_data)
        inactive = {**resource_data, "resource_path": "/other", "is_active": False}
        await repo.create_resource(inactive)
        await db_session.commit()

        items, total = await repo.list_resources(filters={"is_active": True})
        assert total == 1

        items, total = await repo.list_resources(filters={"is_active": False})
        assert total == 1

    async def test_list_resources_pagination(self, db_session, resource_data):
        repo = SessionAccessControlRepository(db_session)
        for i in range(3):
            data = {**resource_data, "resource_path": f"/page/{i}", "resource_name": f"Page {i}"}
            await repo.create_resource(data)
        await db_session.commit()

        items, total = await repo.list_resources(page=1, page_size=2)
        assert total == 3
        assert len(items) == 2

    async def test_update_resource(self, db_session, resource_data):
        repo = SessionAccessControlRepository(db_session)
        created = await repo.create_resource(resource_data)
        await db_session.commit()

        updated = await repo.update_resource(created.id, {"resource_name": "Updated Name"})
        await db_session.commit()
        assert updated.resource_name == "Updated Name"

    async def test_update_resource_not_found(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        result = await repo.update_resource(uuid.uuid4(), {"resource_name": "x"})
        assert result is None

    async def test_delete_resource(self, db_session, resource_data):
        repo = SessionAccessControlRepository(db_session)
        created = await repo.create_resource(resource_data)
        await db_session.commit()

        deleted = await repo.delete_resource(created.id)
        await db_session.commit()
        assert deleted is True

        fetched = await repo.get_resource(created.id)
        assert fetched is None

    async def test_delete_resource_not_found(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        result = await repo.delete_resource(uuid.uuid4())
        assert result is False


class TestRecordRepository:
    async def test_create_record(self, db_session, record_data):
        repo = SessionAccessControlRepository(db_session)
        obj = await repo.create_record(record_data)
        await db_session.commit()
        assert obj.id is not None
        assert obj.session_status.value == "active"
        assert obj.outcome.value == "allowed"

    async def test_create_record_without_resource(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        data = {
            "session_token": None,
            "session_status": "anonymous",
            "action_type": "page_view",
            "outcome": "denied_guest",
            "denial_reason": "Authentication required",
        }
        obj = await repo.create_record(data)
        await db_session.commit()
        assert obj.id is not None
        assert obj.resource_id is None

    async def test_list_records_empty(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        items, total = await repo.list_records()
        assert items == []
        assert total == 0

    async def test_list_records_returns_created(self, db_session, record_data):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_record(record_data)
        await db_session.commit()

        items, total = await repo.list_records()
        assert total == 1
        assert len(items) == 1

    async def test_list_records_filter_by_session_status(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_record({"session_status": "active", "action_type": "page_view", "outcome": "allowed"})
        await repo.create_record({"session_status": "anonymous", "action_type": "page_view", "outcome": "denied_guest"})
        await db_session.commit()

        items, total = await repo.list_records(filters={"session_status": "active"})
        assert total == 1

    async def test_list_records_filter_by_outcome(self, db_session):
        repo = SessionAccessControlRepository(db_session)
        await repo.create_record({"session_status": "active", "action_type": "page_view", "outcome": "allowed"})
        await repo.create_record({"session_status": "anonymous", "action_type": "page_view", "outcome": "denied_guest"})
        await db_session.commit()

        items, total = await repo.list_records(filters={"outcome": "denied_guest"})
        assert total == 1
