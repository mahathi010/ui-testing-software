"""Unit tests for session access control service logic."""

import pytest

from app.login_mgmt.login_flow_backend.session_access_control.schema import (
    AccessOutcomeEnum,
    ProtectionLevelEnum,
    SessionStatusEnum,
)
from app.login_mgmt.login_flow_backend.session_access_control.service import (
    _determine_outcome,
    _resolve_session_status,
)


class TestResolveSessionStatus:
    """Unit tests for _resolve_session_status helper."""

    def test_none_returns_anonymous(self):
        assert _resolve_session_status(None) == SessionStatusEnum.anonymous

    def test_empty_string_returns_anonymous(self):
        assert _resolve_session_status("") == SessionStatusEnum.anonymous

    def test_valid_prefix_returns_active(self):
        assert _resolve_session_status("valid_user_123") == SessionStatusEnum.active

    def test_valid_prefix_minimal(self):
        assert _resolve_session_status("valid_") == SessionStatusEnum.active

    def test_expired_prefix_returns_expired(self):
        assert _resolve_session_status("expired_user_123") == SessionStatusEnum.expired

    def test_expired_prefix_minimal(self):
        assert _resolve_session_status("expired_") == SessionStatusEnum.expired

    def test_invalid_prefix_returns_invalid(self):
        assert _resolve_session_status("invalid_xyz") == SessionStatusEnum.invalid

    def test_unknown_token_returns_invalid(self):
        assert _resolve_session_status("some_random_token") == SessionStatusEnum.invalid

    def test_whitespace_token_returns_invalid(self):
        assert _resolve_session_status("   ") == SessionStatusEnum.invalid

    def test_token_with_valid_in_middle_returns_invalid(self):
        assert _resolve_session_status("token_valid_abc") == SessionStatusEnum.invalid


class TestDetermineOutcome:
    """Unit tests for _determine_outcome covering all session × protection combinations."""

    # Anonymous × * combinations
    def test_anonymous_on_public_allowed(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.anonymous, ProtectionLevelEnum.public
        )
        assert outcome == AccessOutcomeEnum.allowed
        assert reason is None
        assert redirect is None

    def test_anonymous_on_authenticated_denied_guest(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.anonymous, ProtectionLevelEnum.authenticated
        )
        assert outcome == AccessOutcomeEnum.denied_guest
        assert reason is not None
        assert redirect == "/login"

    def test_anonymous_on_elevated_denied_guest(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.anonymous, ProtectionLevelEnum.elevated
        )
        assert outcome == AccessOutcomeEnum.denied_guest
        assert redirect == "/login"

    # Active × * combinations
    def test_active_on_public_allowed(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.active, ProtectionLevelEnum.public
        )
        assert outcome == AccessOutcomeEnum.allowed

    def test_active_on_authenticated_allowed(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.active, ProtectionLevelEnum.authenticated
        )
        assert outcome == AccessOutcomeEnum.allowed

    def test_active_on_elevated_denied_forbidden(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.active, ProtectionLevelEnum.elevated
        )
        assert outcome == AccessOutcomeEnum.denied_forbidden
        assert reason is not None
        assert redirect is None

    # Expired × * combinations
    def test_expired_on_public_allowed(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.expired, ProtectionLevelEnum.public
        )
        assert outcome == AccessOutcomeEnum.allowed

    def test_expired_on_authenticated_denied_expired(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.expired, ProtectionLevelEnum.authenticated
        )
        assert outcome == AccessOutcomeEnum.denied_expired
        assert redirect == "/login"

    def test_expired_on_elevated_denied_expired(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.expired, ProtectionLevelEnum.elevated
        )
        assert outcome == AccessOutcomeEnum.denied_expired
        assert redirect == "/login"

    # Invalid × * combinations
    def test_invalid_on_public_allowed(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.invalid, ProtectionLevelEnum.public
        )
        assert outcome == AccessOutcomeEnum.allowed

    def test_invalid_on_authenticated_denied_invalid(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.invalid, ProtectionLevelEnum.authenticated
        )
        assert outcome == AccessOutcomeEnum.denied_invalid
        assert reason is not None

    def test_invalid_on_elevated_denied_invalid(self):
        outcome, reason, redirect = _determine_outcome(
            SessionStatusEnum.invalid, ProtectionLevelEnum.elevated
        )
        assert outcome == AccessOutcomeEnum.denied_invalid

    # Outcome boolean semantics
    def test_allowed_outcomes_are_only_allowed(self):
        allowed_combinations = [
            (SessionStatusEnum.anonymous, ProtectionLevelEnum.public),
            (SessionStatusEnum.active, ProtectionLevelEnum.public),
            (SessionStatusEnum.active, ProtectionLevelEnum.authenticated),
            (SessionStatusEnum.expired, ProtectionLevelEnum.public),
            (SessionStatusEnum.invalid, ProtectionLevelEnum.public),
        ]
        for ss, pl in allowed_combinations:
            outcome, _, _ = _determine_outcome(ss, pl)
            assert outcome == AccessOutcomeEnum.allowed, f"Expected allowed for {ss}×{pl}"

    def test_denied_outcomes_are_not_allowed(self):
        denied_combinations = [
            (SessionStatusEnum.anonymous, ProtectionLevelEnum.authenticated),
            (SessionStatusEnum.anonymous, ProtectionLevelEnum.elevated),
            (SessionStatusEnum.active, ProtectionLevelEnum.elevated),
            (SessionStatusEnum.expired, ProtectionLevelEnum.authenticated),
            (SessionStatusEnum.expired, ProtectionLevelEnum.elevated),
            (SessionStatusEnum.invalid, ProtectionLevelEnum.authenticated),
            (SessionStatusEnum.invalid, ProtectionLevelEnum.elevated),
        ]
        for ss, pl in denied_combinations:
            outcome, _, _ = _determine_outcome(ss, pl)
            assert outcome != AccessOutcomeEnum.allowed, f"Expected denied for {ss}×{pl}"

    # Redirect semantics
    def test_redirect_present_for_guest_denied(self):
        _, _, redirect = _determine_outcome(
            SessionStatusEnum.anonymous, ProtectionLevelEnum.authenticated
        )
        assert redirect is not None

    def test_redirect_present_for_expired_denied(self):
        _, _, redirect = _determine_outcome(
            SessionStatusEnum.expired, ProtectionLevelEnum.authenticated
        )
        assert redirect is not None

    def test_no_redirect_for_forbidden(self):
        _, _, redirect = _determine_outcome(
            SessionStatusEnum.active, ProtectionLevelEnum.elevated
        )
        assert redirect is None

    def test_no_redirect_for_invalid(self):
        _, _, redirect = _determine_outcome(
            SessionStatusEnum.invalid, ProtectionLevelEnum.authenticated
        )
        assert redirect is None
