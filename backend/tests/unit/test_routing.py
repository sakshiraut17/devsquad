"""Unit tests for workflow routing and bounded repair conditional edges."""

import pytest
from app.orchestration.routing import (
    route_after_coder,
    route_after_context,
    route_after_planner,
    route_after_reviewer,
    route_after_tester,
    route_after_validation,
)
from app.orchestration.state import DevSquadState, WorkflowStatus


def test_route_after_validation():
    state_ok: DevSquadState = {"status": WorkflowStatus.RUNNING.value}
    assert route_after_validation(state_ok) == "context_preparation_node"

    state_fail: DevSquadState = {"status": WorkflowStatus.FAILED.value}
    assert route_after_validation(state_fail) == "finalization_node"


def test_route_after_planner():
    state_ok: DevSquadState = {"status": WorkflowStatus.RUNNING.value, "plan": {"steps": []}}
    assert route_after_planner(state_ok) == "coder_node"

    state_no_plan: DevSquadState = {"status": WorkflowStatus.RUNNING.value, "plan": None}
    assert route_after_planner(state_no_plan) == "finalization_node"


def test_route_after_coder():
    state_ok: DevSquadState = {"status": WorkflowStatus.RUNNING.value, "current_patch": {"unified_diff": "..."}}
    assert route_after_coder(state_ok) == "sandbox_tester_node"

    state_no_patch: DevSquadState = {"status": WorkflowStatus.RUNNING.value, "current_patch": None}
    assert route_after_coder(state_no_patch) == "finalization_node"


def test_route_after_tester():
    state_ok: DevSquadState = {"status": WorkflowStatus.RUNNING.value, "test_result": {"status": "PARTIAL_VALIDATION"}}
    assert route_after_tester(state_ok) == "reviewer_node"


def test_route_after_reviewer_approve():
    state_approved: DevSquadState = {
        "run_id": "run-1",
        "status": WorkflowStatus.RUNNING.value,
        "test_result": {"status": "TESTS_PASSED"},
        "review_result": {
            "recommendation": "approve",
            "findings": [{"severity": "INFO"}],
        },
        "repair_attempts": 0,
        "max_repair_attempts": 3,
    }
    assert route_after_reviewer(state_approved) == "finalization_node"


def test_route_after_reviewer_approve_without_tests_blocks():
    state_no_tests: DevSquadState = {
        "run_id": "run-1",
        "status": WorkflowStatus.RUNNING.value,
        "review_result": {
            "recommendation": "approve",
            "findings": [{"severity": "INFO"}],
        },
        "repair_attempts": 0,
        "max_repair_attempts": 3,
    }
    assert route_after_reviewer(state_no_tests) == "coder_node"



def test_route_after_reviewer_triggers_bounded_repair():
    # 1. First repair attempt when changes requested
    state_repair_1: DevSquadState = {
        "run_id": "run-1",
        "status": WorkflowStatus.RUNNING.value,
        "review_result": {
            "recommendation": "request_changes",
            "findings": [{"severity": "HIGH", "description": "Fix bug"}],
        },
        "repair_attempts": 0,
        "max_repair_attempts": 3,
    }
    assert route_after_reviewer(state_repair_1) == "coder_node"

    # 2. Second repair attempt
    state_repair_2 = dict(state_repair_1)
    state_repair_2["repair_attempts"] = 1
    assert route_after_reviewer(state_repair_2) == "coder_node"

    # 3. Third repair attempt (current=2, max=3) -> still allows 3rd attempt
    state_repair_3 = dict(state_repair_1)
    state_repair_3["repair_attempts"] = 2
    assert route_after_reviewer(state_repair_3) == "coder_node"

    # 4. Strict cap: when attempts reaches 3 (equal to max_repair_attempts), must STOP
    state_capped = dict(state_repair_1)
    state_capped["repair_attempts"] = 3
    assert route_after_reviewer(state_capped) == "finalization_node"


def test_route_after_reviewer_critical_finding_prevents_direct_approval():
    # Even if model output recommendation said approve, critical finding must trigger repair
    state_critical: DevSquadState = {
        "run_id": "run-1",
        "status": WorkflowStatus.RUNNING.value,
        "review_result": {
            "recommendation": "approve",
            "findings": [{"severity": "CRITICAL", "description": "SQL injection"}],
        },
        "repair_attempts": 0,
        "max_repair_attempts": 3,
    }
    assert route_after_reviewer(state_critical) == "coder_node"
