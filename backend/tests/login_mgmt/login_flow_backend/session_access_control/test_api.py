"""API integration tests for session access control endpoints."""

import pytest

pytestmark = pytest.mark.asyncio

BASE = "/v1/session-access"


@pytest.fixture
def resource_payload():
    return {
        "resource_path": "/api/protected",
        "resource_name": "Protected API",
        "protection_level": "authenticated",
        "is_active": True,
    }


@pytest.fixture
def public_resource_payload():
    return {
        "resource_path": "/api/public",
        "resource_name": "Public API",
        "protection_level": "public",
        "is_active": True,
    }


class TestCheckEndpoint:
    async def test_check_anonymous_on_protected_returns_denied(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        response = await client.post(f"{BASE}/check", json={
            "session_token": None,
            "resource_path": "/api/protected",
            "action_type": "page_view",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["outcome"] == "denied_guest"
        assert data["session_status"] == "anonymous"
        assert data["redirect_url"] == "/login"

    async def test_check_valid_token_on_protected_allowed(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        response = await client.post(f"{BASE}/check", json={
            "session_token": "valid_user_123",
            "resource_path": "/api/protected",
            "action_type": "page_view",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["outcome"] == "allowed"
        assert data["session_status"] == "active"

    async def test_check_expired_token_on_protected_denied(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        response = await client.post(f"{BASE}/check", json={
            "session_token": "expired_user_123",
            "resource_path": "/api/protected",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["outcome"] == "denied_expired"
        assert data["session_status"] == "expired"

    async def test_check_invalid_token_on_protected_denied(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        response = await client.post(f"{BASE}/check", json={
            "session_token": "invalid_xyz",
            "resource_path": "/api/protected",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["outcome"] == "denied_invalid"
        assert data["session_status"] == "invalid"

    async def test_check_creates_record(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        check_resp = await client.post(f"{BASE}/check", json={
            "session_token": "valid_user_123",
            "resource_path": "/api/protected",
        })
        assert check_resp.json()["record_id"] is not None

        records_resp = await client.get(f"{BASE}/records")
        assert records_resp.json()["total"] == 1


class TestGuardEndpoint:
    async def test_guard_guest_denied(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        response = await client.post(f"{BASE}/guard", json={
            "session_token": None,
            "resource_path": "/api/protected",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["outcome"] == "denied_guest"

    async def test_guard_valid_token_allowed(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        response = await client.post(f"{BASE}/guard", json={
            "session_token": "valid_user_123",
            "resource_path": "/api/protected",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["outcome"] == "allowed"


class TestResourcesAPI:
    async def test_create_resource(self, client, resource_payload):
        response = await client.post(f"{BASE}/resources", json=resource_payload)
        assert response.status_code == 201
        data = response.json()
        assert data["resource_path"] == resource_payload["resource_path"]
        assert data["resource_name"] == resource_payload["resource_name"]
        assert "id" in data

    async def test_create_resource_missing_path_returns_422(self, client):
        response = await client.post(f"{BASE}/resources", json={"resource_name": "Test"})
        assert response.status_code == 422

    async def test_list_resources_empty(self, client):
        response = await client.get(f"{BASE}/resources")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_resources_returns_created(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        response = await client.get(f"{BASE}/resources")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_list_resources_filter_by_is_active(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        response = await client.get(f"{BASE}/resources?is_active=true")
        assert response.status_code == 200
        assert response.json()["total"] == 1

        response = await client.get(f"{BASE}/resources?is_active=false")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_list_resources_pagination(self, client, resource_payload):
        for i in range(3):
            payload = {**resource_payload, "resource_path": f"/path/{i}", "resource_name": f"Resource {i}"}
            await client.post(f"{BASE}/resources", json=payload)

        response = await client.get(f"{BASE}/resources?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    async def test_get_resource(self, client, resource_payload):
        create_resp = await client.post(f"{BASE}/resources", json=resource_payload)
        resource_id = create_resp.json()["id"]

        response = await client.get(f"{BASE}/resources/{resource_id}")
        assert response.status_code == 200
        assert response.json()["id"] == resource_id

    async def test_get_resource_not_found(self, client):
        response = await client.get(f"{BASE}/resources/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    async def test_update_resource(self, client, resource_payload):
        create_resp = await client.post(f"{BASE}/resources", json=resource_payload)
        resource_id = create_resp.json()["id"]

        response = await client.put(
            f"{BASE}/resources/{resource_id}",
            json={"resource_name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["resource_name"] == "Updated Name"

    async def test_update_resource_not_found(self, client):
        response = await client.put(
            f"{BASE}/resources/00000000-0000-0000-0000-000000000000",
            json={"resource_name": "x"},
        )
        assert response.status_code == 404

    async def test_delete_resource(self, client, resource_payload):
        create_resp = await client.post(f"{BASE}/resources", json=resource_payload)
        resource_id = create_resp.json()["id"]

        response = await client.delete(f"{BASE}/resources/{resource_id}")
        assert response.status_code == 204

        get_resp = await client.get(f"{BASE}/resources/{resource_id}")
        assert get_resp.status_code == 404

    async def test_delete_resource_not_found(self, client):
        response = await client.delete(f"{BASE}/resources/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestRecordsAPI:
    async def test_list_records_empty(self, client):
        response = await client.get(f"{BASE}/records")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_create_record(self, client):
        response = await client.post(f"{BASE}/records", json={
            "session_token": "valid_user_123",
            "session_status": "active",
            "action_type": "page_view",
            "outcome": "allowed",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["outcome"] == "allowed"
        assert "id" in data

    async def test_list_records_after_check(self, client, resource_payload):
        await client.post(f"{BASE}/resources", json=resource_payload)
        await client.post(f"{BASE}/check", json={
            "session_token": "valid_user_123",
            "resource_path": "/api/protected",
        })

        response = await client.get(f"{BASE}/records")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_list_records_filter_by_session_status(self, client):
        await client.post(f"{BASE}/records", json={
            "session_status": "active",
            "action_type": "page_view",
            "outcome": "allowed",
        })
        await client.post(f"{BASE}/records", json={
            "session_status": "anonymous",
            "action_type": "page_view",
            "outcome": "denied_guest",
        })

        response = await client.get(f"{BASE}/records?session_status=active")
        assert response.status_code == 200
        assert response.json()["total"] == 1
