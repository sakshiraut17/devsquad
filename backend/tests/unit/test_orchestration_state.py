"""Unit tests for DevSquad orchestration state and stage enums."""

from app.orchestration.state import (
    DevSquadState,
    WorkflowStage,
    WorkflowStatus,
    create_initial_state,
)


def test_create_initial_state_defaults():
    state = create_initial_state(
        run_id="run-test-1",
        repository_id="repo-1",
        issue_id="issue-1",
        max_repair_attempts=3,
        metadata={"custom": "val"},
    )

    assert state["run_id"] == "run-test-1"
    assert state["thread_id"] == "thread-run-test-1"
    assert state["status"] == WorkflowStatus.PENDING.value
    assert state["current_stage"] == WorkflowStage.INPUT_VALIDATION.value
    assert state["patch_revision"] == 0
    assert state["repair_attempts"] == 0
    assert state["max_repair_attempts"] == 3
    assert state["plan"] is None
    assert state["current_patch"] is None
    assert state["test_result"] is None
    assert state["review_result"] is None
    assert state["metadata"]["custom"] == "val"
    assert state["started_at"] is not None


def test_workflow_enums():
    assert WorkflowStatus.PENDING == "PENDING"
    assert WorkflowStatus.RUNNING == "RUNNING"
    assert WorkflowStatus.WAITING_FOR_APPROVAL == "WAITING_FOR_APPROVAL"
    assert WorkflowStatus.COMPLETED == "COMPLETED"
    assert WorkflowStatus.FAILED == "FAILED"
    assert WorkflowStatus.CANCELLED == "CANCELLED"
    assert WorkflowStatus.INTERRUPTED == "INTERRUPTED"

    assert WorkflowStage.INPUT_VALIDATION == "INPUT_VALIDATION"
    assert WorkflowStage.PLANNING == "PLANNING"
    assert WorkflowStage.CODING == "CODING"
    assert WorkflowStage.TESTING == "TESTING"
    assert WorkflowStage.REVIEWING == "REVIEWING"
    assert WorkflowStage.FINALIZING == "FINALIZING"
