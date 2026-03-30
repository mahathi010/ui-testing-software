"""API integration tests for session access control endpoints."""

import pytest


pytestmark = pytest.mark.asyncio

BASE = "/v1/session-access-control"


@pytest.fixture
def sac_definition_payload():
    return {
        "name": "Test Session Access Control",
        "target_url": "https://example.com/dashboard",
        "version": "1.0",
        "page_identity_indicator": "Dashboard | Example",
        "viewport_width": 1280,
        "viewport_height": 720,
        "clean_session_required": True,
        "is_active": True,
    }


@pytest.fixture
def sac_execution_payload():
    def _make(definition_id: str, session_state: str = "authenticated") -> dict:
        return {
            "definition_id": definition_id,
            "target_url": "https://example.com/dashboard",
            "target_version": "1.0",
            "session_state": session_state,
            "status": "pending",
        }
    return _make


class TestHealthEndpoint:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ui_testing_software"


class TestDefinitionsAPI:
    async def test_create_definition(self, client, sac_definition_payload):
        response = await client.post(f"{BASE}/definitions", json=sac_definition_payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sac_definition_payload["name"]
        assert data["target_url"] == sac_definition_payload["target_url"]
        assert "id" in data
        assert "created_at" in data
        assert "requirements" in data
        assert isinstance(data["requirements"], list)
        assert len(data["requirements"]) == 30

    async def test_create_definition_injects_default_requirements(self, client, sac_definition_payload):
        response = await client.post(f"{BASE}/definitions", json=sac_definition_payload)
        assert response.status_code == 201
        requirements = response.json()["requirements"]
        fr_ids = [r["fr_id"] for r in requirements]
        assert "FR-1" in fr_ids
        assert "FR-30" in fr_ids

    async def test_create_definition_missing_name_returns_422(self, client):
        response = await client.post(
            f"{BASE}/definitions",
            json={"target_url": "https://example.com/dashboard"},
        )
        assert response.status_code == 422

    async def test_create_definition_missing_target_url_returns_422(self, client):
        response = await client.post(
            f"{BASE}/definitions",
            json={"name": "Test"},
        )
        assert response.status_code == 422

    async def test_get_definition(self, client, sac_definition_payload):
        create_resp = await client.post(f"{BASE}/definitions", json=sac_definition_payload)
        definition_id = create_resp.json()["id"]

        response = await client.get(f"{BASE}/definitions/{definition_id}")
        assert response.status_code == 200
        assert response.json()["id"] == definition_id

    async def test_get_definition_not_found(self, client):
        response = await client.get(
            f"{BASE}/definitions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_list_definitions_empty(self, client):
        response = await client.get(f"{BASE}/definitions")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    async def test_list_definitions_returns_created(self, client, sac_definition_payload):
        await client.post(f"{BASE}/definitions", json=sac_definition_payload)
        response = await client.get(f"{BASE}/definitions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_list_definitions_filter_by_is_active(self, client, sac_definition_payload):
        await client.post(f"{BASE}/definitions", json=sac_definition_payload)
        response = await client.get(f"{BASE}/definitions?is_active=true")
        assert response.status_code == 200
        assert response.json()["total"] == 1

        response = await client.get(f"{BASE}/definitions?is_active=false")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_list_definitions_filter_by_name(self, client, sac_definition_payload):
        await client.post(f"{BASE}/definitions", json=sac_definition_payload)
        response = await client.get(f"{BASE}/definitions?name=Session")
        assert response.status_code == 200
        assert response.json()["total"] == 1

        response = await client.get(f"{BASE}/definitions?name=nonexistent_xyz")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_list_definitions_pagination(self, client, sac_definition_payload):
        for i in range(3):
            payload = {**sac_definition_payload, "name": f"Definition {i}"}
            await client.post(f"{BASE}/definitions", json=payload)

        response = await client.get(f"{BASE}/definitions?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_update_definition(self, client, sac_definition_payload):
        create_resp = await client.post(f"{BASE}/definitions", json=sac_definition_payload)
        definition_id = create_resp.json()["id"]

        response = await client.put(
            f"{BASE}/definitions/{definition_id}",
            json={"name": "Updated Session Definition"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Session Definition"

    async def test_update_definition_not_found(self, client):
        response = await client.put(
            f"{BASE}/definitions/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated"},
        )
        assert response.status_code == 404

    async def test_delete_definition(self, client, sac_definition_payload):
        create_resp = await client.post(f"{BASE}/definitions", json=sac_definition_payload)
        definition_id = create_resp.json()["id"]

        response = await client.delete(f"{BASE}/definitions/{definition_id}")
        assert response.status_code == 204

        get_resp = await client.get(f"{BASE}/definitions/{definition_id}")
        assert get_resp.status_code == 404

    async def test_delete_definition_not_found(self, client):
        response = await client.delete(
            f"{BASE}/definitions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestExecutionsAPI:
    async def _create_definition(self, client, sac_definition_payload):
        resp = await client.post(f"{BASE}/definitions", json=sac_definition_payload)
        return resp.json()["id"]

    async def test_create_execution(self, client, sac_definition_payload, sac_execution_payload):
        definition_id = await self._create_definition(client, sac_definition_payload)
        payload = sac_execution_payload(definition_id)
        response = await client.post(f"{BASE}/executions", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["definition_id"] == definition_id
        assert data["status"] == "pending"
        assert data["session_state"] == "authenticated"
        assert "id" in data

    async def test_create_execution_definition_not_found(self, client, sac_execution_payload):
        payload = sac_execution_payload("00000000-0000-0000-0000-000000000000")
        response = await client.post(f"{BASE}/executions", json=payload)
        assert response.status_code == 404

    async def test_get_execution(self, client, sac_definition_payload, sac_execution_payload):
        definition_id = await self._create_definition(client, sac_definition_payload)
        create_resp = await client.post(
            f"{BASE}/executions", json=sac_execution_payload(definition_id)
        )
        execution_id = create_resp.json()["id"]

        response = await client.get(f"{BASE}/executions/{execution_id}")
        assert response.status_code == 200
        assert response.json()["id"] == execution_id

    async def test_get_execution_not_found(self, client):
        response = await client.get(
            f"{BASE}/executions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_list_executions_empty(self, client):
        response = await client.get(f"{BASE}/executions")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_executions_filter_by_definition_id(
        self, client, sac_definition_payload, sac_execution_payload
    ):
        definition_id = await self._create_definition(client, sac_definition_payload)
        await client.post(f"{BASE}/executions", json=sac_execution_payload(definition_id))

        response = await client.get(f"{BASE}/executions?definition_id={definition_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_list_executions_filter_by_session_state(
        self, client, sac_definition_payload, sac_execution_payload
    ):
        definition_id = await self._create_definition(client, sac_definition_payload)
        await client.post(
            f"{BASE}/executions", json=sac_execution_payload(definition_id, "authenticated")
        )
        await client.post(
            f"{BASE}/executions", json=sac_execution_payload(definition_id, "guest")
        )

        response = await client.get(f"{BASE}/executions?session_state=authenticated")
        assert response.status_code == 200
        assert response.json()["total"] == 1

        response = await client.get(f"{BASE}/executions?session_state=guest")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_update_execution_status_transition(
        self, client, sac_definition_payload, sac_execution_payload
    ):
        definition_id = await self._create_definition(client, sac_definition_payload)
        create_resp = await client.post(
            f"{BASE}/executions", json=sac_execution_payload(definition_id)
        )
        execution_id = create_resp.json()["id"]

        response = await client.put(
            f"{BASE}/executions/{execution_id}",
            json={"status": "running"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    async def test_update_execution_invalid_transition(
        self, client, sac_definition_payload, sac_execution_payload
    ):
        definition_id = await self._create_definition(client, sac_definition_payload)
        create_resp = await client.post(
            f"{BASE}/executions", json=sac_execution_payload(definition_id)
        )
        execution_id = create_resp.json()["id"]

        # pending → passed is not a valid transition
        response = await client.put(
            f"{BASE}/executions/{execution_id}",
            json={"status": "passed"},
        )
        assert response.status_code == 422

    async def test_update_execution_not_found(self, client):
        response = await client.put(
            f"{BASE}/executions/00000000-0000-0000-0000-000000000000",
            json={"status": "running"},
        )
        assert response.status_code == 404

    async def test_full_execution_lifecycle(
        self, client, sac_definition_payload, sac_execution_payload
    ):
        definition_id = await self._create_definition(client, sac_definition_payload)
        create_resp = await client.post(
            f"{BASE}/executions", json=sac_execution_payload(definition_id)
        )
        execution_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "pending"

        run_resp = await client.put(
            f"{BASE}/executions/{execution_id}", json={"status": "running"}
        )
        assert run_resp.status_code == 200
        assert run_resp.json()["status"] == "running"

        pass_resp = await client.put(
            f"{BASE}/executions/{execution_id}", json={"status": "passed"}
        )
        assert pass_resp.status_code == 200
        assert pass_resp.json()["status"] == "passed"
