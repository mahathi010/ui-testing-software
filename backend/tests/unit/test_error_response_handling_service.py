"""Pure-unit tests for error response handling service logic (no database)."""

import pytest

from app.login_mgmt.login_flow_backend.error_response_handling.service import (
    _build_default_requirements,
    _VALID_EXECUTION_TRANSITIONS,
    _SUPPORTED_DEFINITION_FILTERS,
    _SUPPORTED_EXECUTION_FILTERS,
)
from app.login_mgmt.login_flow_backend.error_response_handling.schema import ExecutionStatusEnum


class TestDefaultRequirements:
    def test_returns_list_of_24(self):
        reqs = _build_default_requirements()
        assert isinstance(reqs, list)
        assert len(reqs) == 24

    def test_all_have_required_keys(self):
        reqs = _build_default_requirements()
        required_keys = {"fr_id", "description", "lifecycle_section", "acceptance_signal", "applicability"}
        for req in reqs:
            assert required_keys.issubset(req.keys()), f"Missing keys in {req}"

    def test_fr_ids_are_sequential_from_1_to_24(self):
        reqs = _build_default_requirements()
        fr_ids = [r["fr_id"] for r in reqs]
        expected = [f"FR-{i}" for i in range(1, 25)]
        assert fr_ids == expected

    def test_lifecycle_sections_cover_four_groups(self):
        reqs = _build_default_requirements()
        sections = {r["lifecycle_section"] for r in reqs}
        assert "initial_load" in sections
        assert "page_structure" in sections
        assert "interactions" in sections
        assert "error_handling" in sections

    def test_fr1_to_fr6_in_initial_load(self):
        reqs = _build_default_requirements()
        initial_load = [r for r in reqs if r["lifecycle_section"] == "initial_load"]
        fr_ids = [r["fr_id"] for r in initial_load]
        for fr_id in ["FR-1", "FR-2", "FR-3", "FR-4", "FR-5", "FR-6"]:
            assert fr_id in fr_ids

    def test_fr19_to_fr24_in_error_handling(self):
        reqs = _build_default_requirements()
        error_handling = [r for r in reqs if r["lifecycle_section"] == "error_handling"]
        fr_ids = [r["fr_id"] for r in error_handling]
        for fr_id in ["FR-19", "FR-20", "FR-21", "FR-22", "FR-24"]:
            assert fr_id in fr_ids


class TestExecutionTransitions:
    def test_pending_can_transition_to_running_or_skipped(self):
        allowed = _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.pending]
        assert ExecutionStatusEnum.running in allowed
        assert ExecutionStatusEnum.skipped in allowed

    def test_pending_cannot_transition_to_passed_directly(self):
        allowed = _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.pending]
        assert ExecutionStatusEnum.passed not in allowed

    def test_running_can_transition_to_passed_failed_error(self):
        allowed = _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.running]
        assert ExecutionStatusEnum.passed in allowed
        assert ExecutionStatusEnum.failed in allowed
        assert ExecutionStatusEnum.error in allowed

    def test_passed_has_no_transitions(self):
        allowed = _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.passed]
        assert len(allowed) == 0

    def test_failed_can_retry_to_pending(self):
        allowed = _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.failed]
        assert ExecutionStatusEnum.pending in allowed

    def test_error_can_retry_to_pending(self):
        allowed = _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.error]
        assert ExecutionStatusEnum.pending in allowed

    def test_skipped_can_reset_to_pending(self):
        allowed = _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.skipped]
        assert ExecutionStatusEnum.pending in allowed


class TestSupportedFilters:
    def test_definition_filters_include_is_active_and_name(self):
        assert "is_active" in _SUPPORTED_DEFINITION_FILTERS
        assert "name" in _SUPPORTED_DEFINITION_FILTERS

    def test_execution_filters_include_definition_id_and_status(self):
        assert "definition_id" in _SUPPORTED_EXECUTION_FILTERS
        assert "status" in _SUPPORTED_EXECUTION_FILTERS

    def test_definition_filters_do_not_include_unknown_fields(self):
        assert "target_url" not in _SUPPORTED_DEFINITION_FILTERS
        assert "version" not in _SUPPORTED_DEFINITION_FILTERS

    def test_execution_filters_do_not_include_unknown_fields(self):
        assert "target_url" not in _SUPPORTED_EXECUTION_FILTERS
        assert "name" not in _SUPPORTED_EXECUTION_FILTERS
