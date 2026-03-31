"""API integration tests for error response handling endpoints."""

import pytest

pytestmark = pytest.mark.asyncio

_DEF_PAYLOAD = {
    "name": "Error Response Test Definition",
    "target_url": "https://example.com/error-page",
    "version": "1.0",
    "page_identity_indicator": "Error | Example",
    "viewport_width": 1280,
    "viewport_height": 720,
    "is_active": True,
}


class TestDefinitionsAPI:
    async def test_create_definition(self, client):
        response = await client.post("/v1/error-response/definitions", json=_DEF_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == _DEF_PAYLOAD["name"]
        assert data["target_url"] == _DEF_PAYLOAD["target_url"]
        assert "id" in data
        assert "created_at" in data
        assert "requirements" in data
        assert isinstance(data["requirements"], list)
        assert len(data["requirements"]) == 24

    async def test_create_definition_injects_default_requirements(self, client):
        response = await client.post("/v1/error-response/definitions", json=_DEF_PAYLOAD)
        assert response.status_code == 201
        requirements = response.json()["requirements"]
        fr_ids = [r["fr_id"] for r in requirements]
        assert "FR-1" in fr_ids
        assert "FR-24" in fr_ids

    async def test_create_definition_missing_name_returns_422(self, client):
        response = await client.post(
            "/v1/error-response/definitions",
            json={"target_url": "https://example.com/error-page"},
        )
        assert response.status_code == 422

    async def test_create_definition_missing_target_url_returns_422(self, client):
        response = await client.post(
            "/v1/error-response/definitions",
            json={"name": "Test"},
        )
        assert response.status_code == 422

    async def test_get_definition(self, client):
        create_resp = await client.post("/v1/error-response/definitions", json=_DEF_PAYLOAD)
        definition_id = create_resp.json()["id"]

        response = await client.get(f"/v1/error-response/definitions/{definition_id}")
        assert response.status_code == 200
        assert response.json()["id"] == definition_id

    async def test_get_definition_not_found(self, client):
        response = await client.get(
            "/v1/error-response/definitions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_list_definitions_empty(self, client):
        response = await client.get("/v1/error-response/definitions")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    async def test_list_definitions_returns_created(self, client):
        await client.post("/v1/error-response/definitions", json=_DEF_PAYLOAD)
        response = await client.get("/v1/error-response/definitions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_list_definitions_filter_by_is_active(self, client):
        await client.post("/v1/error-response/definitions", json=_DEF_PAYLOAD)
        response = await client.get("/v1/error-response/definitions?is_active=true")
        assert response.status_code == 200
        assert response.json()["total"] == 1

        response = await client.get("/v1/error-response/definitions?is_active=false")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_list_definitions_pagination(self, client):
        for i in range(3):
            payload = {**_DEF_PAYLOAD, "name": f"Definition {i}"}
            await client.post("/v1/error-response/definitions", json=payload)

        response = await client.get("/v1/error-response/definitions?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_update_definition(self, client):
        create_resp = await client.post("/v1/error-response/definitions", json=_DEF_PAYLOAD)
        definition_id = create_resp.json()["id"]

        response = await client.put(
            f"/v1/error-response/definitions/{definition_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_update_definition_not_found(self, client):
        response = await client.put(
            "/v1/error-response/definitions/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated"},
        )
        assert response.status_code == 404

    async def test_delete_definition(self, client):
        create_resp = await client.post("/v1/error-response/definitions", json=_DEF_PAYLOAD)
        definition_id = create_resp.json()["id"]

        response = await client.delete(f"/v1/error-response/definitions/{definition_id}")
        assert response.status_code == 204

        get_resp = await client.get(f"/v1/error-response/definitions/{definition_id}")
        assert get_resp.status_code == 404

    async def test_delete_definition_not_found(self, client):
        response = await client.delete(
            "/v1/error-response/definitions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestExecutionsAPI:
    async def _create_definition(self, client):
        resp = await client.post("/v1/error-response/definitions", json=_DEF_PAYLOAD)
        return resp.json()["id"]

    async def test_create_execution(self, client):
        definition_id = await self._create_definition(client)
        payload = {"definition_id": definition_id, "status": "pending"}
        response = await client.post("/v1/error-response/executions", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["definition_id"] == definition_id
        assert data["status"] == "pending"
        assert "id" in data

    async def test_create_execution_definition_not_found(self, client):
        payload = {"definition_id": "00000000-0000-0000-0000-000000000000", "status": "pending"}
        response = await client.post("/v1/error-response/executions", json=payload)
        assert response.status_code == 404

    async def test_get_execution(self, client):
        definition_id = await self._create_definition(client)
        create_resp = await client.post(
            "/v1/error-response/executions",
            json={"definition_id": definition_id, "status": "pending"},
        )
        execution_id = create_resp.json()["id"]

        response = await client.get(f"/v1/error-response/executions/{execution_id}")
        assert response.status_code == 200
        assert response.json()["id"] == execution_id

    async def test_get_execution_not_found(self, client):
        response = await client.get(
            "/v1/error-response/executions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_list_executions_empty(self, client):
        response = await client.get("/v1/error-response/executions")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_executions_filter_by_definition_id(self, client):
        definition_id = await self._create_definition(client)
        await client.post(
            "/v1/error-response/executions",
            json={"definition_id": definition_id, "status": "pending"},
        )

        response = await client.get(
            f"/v1/error-response/executions?definition_id={definition_id}"
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_update_execution_status_transition(self, client):
        definition_id = await self._create_definition(client)
        create_resp = await client.post(
            "/v1/error-response/executions",
            json={"definition_id": definition_id, "status": "pending"},
        )
        execution_id = create_resp.json()["id"]

        response = await client.put(
            f"/v1/error-response/executions/{execution_id}",
            json={"status": "running"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    async def test_update_execution_invalid_transition(self, client):
        definition_id = await self._create_definition(client)
        create_resp = await client.post(
            "/v1/error-response/executions",
            json={"definition_id": definition_id, "status": "pending"},
        )
        execution_id = create_resp.json()["id"]

        # pending → passed is not a valid transition
        response = await client.put(
            f"/v1/error-response/executions/{execution_id}",
            json={"status": "passed"},
        )
        assert response.status_code == 422

    async def test_update_execution_not_found(self, client):
        response = await client.put(
            "/v1/error-response/executions/00000000-0000-0000-0000-000000000000",
            json={"status": "running"},
        )
        assert response.status_code == 404
