"""Unit tests for credential validation service — pure logic, no DB required."""

import pytest

from app.login_mgmt.login_flow_backend.credential_validation.schema import (
    ApplicabilityEnum,
    ExecutionStatusEnum,
    RequirementSpec,
)
from app.login_mgmt.login_flow_backend.credential_validation.service import (
    _SUPPORTED_DEFINITION_FILTERS,
    _SUPPORTED_EXECUTION_FILTERS,
    _VALID_EXECUTION_TRANSITIONS,
    _build_default_requirements,
)


class TestBuildDefaultRequirements:
    def test_returns_list(self):
        reqs = _build_default_requirements()
        assert isinstance(reqs, list)

    def test_returns_32_requirements(self):
        reqs = _build_default_requirements()
        assert len(reqs) == 32

    def test_all_have_fr_id(self):
        for req in _build_default_requirements():
            assert "fr_id" in req
            assert req["fr_id"].startswith("FR-")

    def test_fr_ids_sequential_1_to_32(self):
        reqs = _build_default_requirements()
        fr_ids = [r["fr_id"] for r in reqs]
        for i in range(1, 33):
            assert f"FR-{i}" in fr_ids

    def test_all_have_required_fields(self):
        for req in _build_default_requirements():
            assert "description" in req
            assert "lifecycle_section" in req
            assert "acceptance_signal" in req
            assert "applicability" in req
            assert "is_required" in req

    def test_lifecycle_sections_covered(self):
        reqs = _build_default_requirements()
        sections = {r["lifecycle_section"] for r in reqs}
        assert "initial_rendering" in sections
        assert "interactions" in sections
        assert "navigation" in sections
        assert "credential_input_flows" in sections
        assert "error_recovery" in sections

    def test_fr1_through_fr6_are_initial_rendering(self):
        reqs = {r["fr_id"]: r for r in _build_default_requirements()}
        for fr_id in ["FR-1", "FR-2", "FR-3", "FR-4", "FR-5", "FR-6"]:
            assert reqs[fr_id]["lifecycle_section"] == "initial_rendering"

    def test_returns_dicts_not_pydantic_models(self):
        reqs = _build_default_requirements()
        assert all(isinstance(r, dict) for r in reqs)


class TestValidExecutionTransitions:
    def test_pending_can_go_to_running(self):
        assert ExecutionStatusEnum.running in _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.pending]

    def test_pending_can_go_to_skipped(self):
        assert ExecutionStatusEnum.skipped in _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.pending]

    def test_pending_cannot_go_to_passed(self):
        assert ExecutionStatusEnum.passed not in _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.pending]

    def test_running_can_go_to_passed(self):
        assert ExecutionStatusEnum.passed in _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.running]

    def test_running_can_go_to_failed(self):
        assert ExecutionStatusEnum.failed in _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.running]

    def test_running_can_go_to_error(self):
        assert ExecutionStatusEnum.error in _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.running]

    def test_passed_has_no_transitions(self):
        assert _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.passed] == set()

    def test_failed_can_reset_to_pending(self):
        assert ExecutionStatusEnum.pending in _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.failed]

    def test_error_can_reset_to_pending(self):
        assert ExecutionStatusEnum.pending in _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.error]

    def test_skipped_can_reset_to_pending(self):
        assert ExecutionStatusEnum.pending in _VALID_EXECUTION_TRANSITIONS[ExecutionStatusEnum.skipped]

    def test_all_statuses_have_transition_entry(self):
        for status in ExecutionStatusEnum:
            assert status in _VALID_EXECUTION_TRANSITIONS


class TestSupportedFilters:
    def test_definition_filters(self):
        assert _SUPPORTED_DEFINITION_FILTERS == {"is_active", "name"}

    def test_execution_filters(self):
        assert _SUPPORTED_EXECUTION_FILTERS == {"definition_id", "status"}


class TestRequirementSpec:
    def test_default_applicability_is_applicable(self):
        req = RequirementSpec(
            fr_id="FR-X",
            description="Test",
            lifecycle_section="initial_rendering",
            acceptance_signal="Signal",
        )
        assert req.applicability == ApplicabilityEnum.applicable

    def test_default_is_required_is_true(self):
        req = RequirementSpec(
            fr_id="FR-X",
            description="Test",
            lifecycle_section="initial_rendering",
            acceptance_signal="Signal",
        )
        assert req.is_required is True

    def test_can_set_all_applicability_values(self):
        for value in ApplicabilityEnum:
            req = RequirementSpec(
                fr_id="FR-X",
                description="Test",
                lifecycle_section="section",
                acceptance_signal="Signal",
                applicability=value,
            )
            assert req.applicability == value


class TestExecutionStatusEnum:
    def test_all_expected_statuses_exist(self):
        statuses = {s.value for s in ExecutionStatusEnum}
        assert statuses == {"pending", "running", "passed", "failed", "error", "skipped"}
