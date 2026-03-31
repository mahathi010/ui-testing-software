"""Service tests for session access control."""

import uuid

import pytest

from app.login_mgmt.login_flow_backend.session_access_control.schema import (
    AccessRecordCreate,
    ActionTypeEnum,
    GuardedActionRequest,
    ResourceCreate,
    ResourceUpdate,
    SessionCheckRequest,
)
from app.login_mgmt.login_flow_backend.session_access_control.service import (
    SessionAccessControlService,
    _resolve_session_status,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def resource_payload():
    return ResourceCreate(
        resource_path="/test/protected",
        resource_name="Test Protected",
        protection_level="authenticated",
    )


@pytest.fixture
def public_resource_payload():
    return ResourceCreate(
        resource_path="/test/public",
        resource_name="Test Public",
        protection_level="public",
    )


class TestResolveSessionStatus:
    def test_none_token_returns_anonymous(self):
        from app.login_mgmt.login_flow_backend.session_access_control.schema import SessionStatusEnum
        assert _resolve_session_status(None) == SessionStatusEnum.anonymous

    def test_empty_token_returns_anonymous(self):
        from app.login_mgmt.login_flow_backend.session_access_control.schema import SessionStatusEnum
        assert _resolve_session_status("") == SessionStatusEnum.anonymous

    def test_valid_prefix_returns_active(self):
        from app.login_mgmt.login_flow_backend.session_access_control.schema import SessionStatusEnum
        assert _resolve_session_status("valid_user_123") == SessionStatusEnum.active

    def test_expired_prefix_returns_expired(self):
        from app.login_mgmt.login_flow_backend.session_access_control.schema import SessionStatusEnum
        assert _resolve_session_status("expired_user_123") == SessionStatusEnum.expired

    def test_invalid_prefix_returns_invalid(self):
        from app.login_mgmt.login_flow_backend.session_access_control.schema import SessionStatusEnum
        assert _resolve_session_status("invalid_xyz") == SessionStatusEnum.invalid

    def test_unknown_prefix_returns_invalid(self):
        from app.login_mgmt.login_flow_backend.session_access_control.schema import SessionStatusEnum
        assert _resolve_session_status("sometoken_abc") == SessionStatusEnum.invalid


class TestResourceService:
    async def test_create_resource(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        result = await svc.create_resource(resource_payload)
        assert result.id is not None
        assert result.resource_name == "Test Protected"

    async def test_get_resource(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        created = await svc.create_resource(resource_payload)
        fetched = await svc.get_resource(created.id)
        assert fetched.id == created.id

    async def test_get_resource_not_found(self, db_session):
        from fastapi import HTTPException
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.get_resource(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_list_resources(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(resource_payload)
        result = await svc.list_resources()
        assert result.total == 1

    async def test_update_resource(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        created = await svc.create_resource(resource_payload)
        updated = await svc.update_resource(created.id, ResourceUpdate(resource_name="New Name"))
        assert updated.resource_name == "New Name"

    async def test_update_resource_not_found(self, db_session):
        from fastapi import HTTPException
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_resource(uuid.uuid4(), ResourceUpdate(resource_name="x"))
        assert exc_info.value.status_code == 404

    async def test_delete_resource(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        created = await svc.create_resource(resource_payload)
        await svc.delete_resource(created.id)
        with pytest.raises(Exception):
            await svc.get_resource(created.id)

    async def test_delete_resource_not_found(self, db_session):
        from fastapi import HTTPException
        svc = SessionAccessControlService(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_resource(uuid.uuid4())
        assert exc_info.value.status_code == 404


class TestCheckSessionAccess:
    async def test_anonymous_on_public_resource_allowed(self, db_session, public_resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(public_resource_payload)

        result = await svc.check_session_access(SessionCheckRequest(
            session_token=None,
            resource_path="/test/public",
        ))
        assert result.is_valid is True
        assert result.outcome.value == "allowed"
        assert result.session_status.value == "anonymous"

    async def test_anonymous_on_protected_resource_denied(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(resource_payload)

        result = await svc.check_session_access(SessionCheckRequest(
            session_token=None,
            resource_path="/test/protected",
        ))
        assert result.is_valid is False
        assert result.outcome.value == "denied_guest"
        assert result.redirect_url == "/login"

    async def test_valid_token_on_protected_resource_allowed(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(resource_payload)

        result = await svc.check_session_access(SessionCheckRequest(
            session_token="valid_user_123",
            resource_path="/test/protected",
        ))
        assert result.is_valid is True
        assert result.outcome.value == "allowed"
        assert result.session_status.value == "active"

    async def test_expired_token_on_protected_resource_denied(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(resource_payload)

        result = await svc.check_session_access(SessionCheckRequest(
            session_token="expired_user_123",
            resource_path="/test/protected",
        ))
        assert result.is_valid is False
        assert result.outcome.value == "denied_expired"
        assert result.redirect_url == "/login"

    async def test_invalid_token_on_protected_resource_denied(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(resource_payload)

        result = await svc.check_session_access(SessionCheckRequest(
            session_token="invalid_xyz",
            resource_path="/test/protected",
        ))
        assert result.is_valid is False
        assert result.outcome.value == "denied_invalid"

    async def test_valid_token_on_elevated_resource_forbidden(self, db_session):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(ResourceCreate(
            resource_path="/test/elevated",
            resource_name="Elevated Resource",
            protection_level="elevated",
        ))

        result = await svc.check_session_access(SessionCheckRequest(
            session_token="valid_user_123",
            resource_path="/test/elevated",
        ))
        assert result.is_valid is False
        assert result.outcome.value == "denied_forbidden"

    async def test_check_creates_record(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(resource_payload)

        result = await svc.check_session_access(SessionCheckRequest(
            session_token="valid_user_123",
            resource_path="/test/protected",
        ))
        assert result.record_id is not None

        records = await svc.list_records()
        assert records.total == 1

    async def test_unknown_resource_path_defaults_to_public(self, db_session):
        svc = SessionAccessControlService(db_session)
        result = await svc.check_session_access(SessionCheckRequest(
            session_token=None,
            resource_path="/unknown/path",
        ))
        assert result.is_valid is True
        assert result.outcome.value == "allowed"


class TestGuardedAction:
    async def test_guest_guarded_action_denied(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(resource_payload)

        result = await svc.attempt_guarded_action(GuardedActionRequest(
            session_token=None,
            resource_path="/test/protected",
        ))
        assert result.allowed is False
        assert result.outcome.value == "denied_guest"
        assert result.redirect_url == "/login"

    async def test_authenticated_guarded_action_allowed(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(resource_payload)

        result = await svc.attempt_guarded_action(GuardedActionRequest(
            session_token="valid_user_123",
            resource_path="/test/protected",
        ))
        assert result.allowed is True
        assert result.outcome.value == "allowed"

    async def test_expired_guarded_action_denied(self, db_session, resource_payload):
        svc = SessionAccessControlService(db_session)
        await svc.create_resource(resource_payload)

        result = await svc.attempt_guarded_action(GuardedActionRequest(
            session_token="expired_user_123",
            resource_path="/test/protected",
        ))
        assert result.allowed is False
        assert result.outcome.value == "denied_expired"

    async def test_unknown_resource_defaults_to_authenticated_protection(self, db_session):
        svc = SessionAccessControlService(db_session)
        result = await svc.attempt_guarded_action(GuardedActionRequest(
            session_token=None,
            resource_path="/unknown/guarded",
        ))
        assert result.allowed is False
        assert result.outcome.value == "denied_guest"


class TestRecordService:
    async def test_create_record(self, db_session):
        svc = SessionAccessControlService(db_session)
        record = await svc.create_record(AccessRecordCreate(
            session_token="valid_user_123",
            session_status="active",
            action_type="page_view",
            outcome="allowed",
        ))
        assert record.id is not None
        assert record.outcome.value == "allowed"

    async def test_list_records(self, db_session):
        svc = SessionAccessControlService(db_session)
        await svc.create_record(AccessRecordCreate(
            session_status="active",
            action_type="page_view",
            outcome="allowed",
        ))
        result = await svc.list_records()
        assert result.total == 1
        assert len(result.items) == 1
