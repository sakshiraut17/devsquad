"""Deterministic routing functions and conditional edge logic for the LangGraph workflow."""

import logging
from typing import Literal
from app.core.config import settings
from app.orchestration.state import DevSquadState, WorkflowStatus

logger = logging.getLogger("devsquad.routing")


def route_after_validation(state: DevSquadState) -> Literal["context_preparation_node", "finalization_node"]:
    """Route after input validation."""
    if state.get("status") in (WorkflowStatus.FAILED.value, WorkflowStatus.CANCELLED.value):
        logger.warning(f"[routing] Validation failed for run {state.get('run_id')}: {state.get('error_message')}")
        return "finalization_node"
    return "context_preparation_node"


def route_after_context(state: DevSquadState) -> Literal["planner_node", "finalization_node"]:
    """Route after context preparation."""
    if state.get("status") in (WorkflowStatus.FAILED.value, WorkflowStatus.CANCELLED.value):
        return "finalization_node"
    return "planner_node"


def route_after_planner(state: DevSquadState) -> Literal["coder_node", "finalization_node"]:
    """Route after planner execution."""
    if state.get("status") in (WorkflowStatus.FAILED.value, WorkflowStatus.CANCELLED.value) or not state.get("plan"):
        return "finalization_node"
    return "coder_node"


def route_after_coder(state: DevSquadState) -> Literal["security_guardian_node", "finalization_node"]:
    """Route after patch generation: proceed to Security Guardian for mandatory evaluation."""
    if state.get("status") in (WorkflowStatus.FAILED.value, WorkflowStatus.CANCELLED.value) or not state.get("current_patch"):
        return "finalization_node"
    return "security_guardian_node"


def route_after_security(state: DevSquadState) -> Literal["sandbox_tester_node", "coder_node", "finalization_node"]:
    """Route after security evaluation: proceed to tester if passed, or trigger bounded repair if blocked."""
    run_id = state.get("run_id")
    if state.get("status") in (WorkflowStatus.FAILED.value, WorkflowStatus.CANCELLED.value):
        return "finalization_node"

    sec_result = state.get("security_result")
    if not sec_result:
        return "finalization_node"

    can_approve = sec_result.get("can_approve", True)
    status_val = sec_result.get("status")

    if status_val == "PASSED" and can_approve:
        logger.info(f"[routing] Run {run_id} passed Security Guardian gate -> sandbox_tester_node.")
        return "sandbox_tester_node"

    # Security blocked: check if repair cycle can be attempted
    current_attempts = state.get("repair_attempts", 0)
    max_attempts = state.get("max_repair_attempts", settings.max_agent_retries)

    if current_attempts < max_attempts:
        logger.info(
            f"[routing] Run {run_id} blocked by Security Guardian (attempt {current_attempts + 1} of {max_attempts}). "
            f"Routing back to coder_node for security repair."
        )
        return "coder_node"
    else:
        logger.warning(
            f"[routing] Run {run_id} exhausted repair attempts on security failure ({max_attempts}). "
            f"Routing to finalization_node."
        )
        return "finalization_node"


def route_after_tester(state: DevSquadState) -> Literal["reviewer_node", "finalization_node"]:
    """Route after sandbox or AST validation."""
    if state.get("status") in (WorkflowStatus.FAILED.value, WorkflowStatus.CANCELLED.value) or not state.get("test_result"):
        return "finalization_node"
    return "reviewer_node"


def route_after_reviewer(
    state: DevSquadState,
) -> Literal["coder_node", "finalization_node"]:
    """Route after review: decide whether to finalize or trigger a bounded repair cycle."""
    run_id = state.get("run_id")
    if state.get("status") in (WorkflowStatus.FAILED.value, WorkflowStatus.CANCELLED.value):
        return "finalization_node"

    review_data = state.get("review_result", {})
    test_data = state.get("test_result", {})
    recommendation = review_data.get("recommendation", "reject")
    has_critical = any(f.get("severity") in ("CRITICAL", "HIGH") for f in review_data.get("findings", []))

    test_status = test_data.get("status")
    test_passed = test_status == "TESTS_PASSED" or (
        test_status in ("PARTIAL_VALIDATION", "SANDBOX_UNAVAILABLE")
        and settings.allow_manual_approval_without_sandbox
    )

    # Clean pass condition: approved, no critical findings, and tests passed/allowed by policy
    if recommendation == "approve" and not has_critical and test_passed:
        logger.info(f"[routing] Run {run_id} approved by reviewer and test gates passed -> Finalizing.")
        return "finalization_node"

    # Execution timeout check
    started_at_str = state.get("started_at")
    if started_at_str:
        try:
            from datetime import datetime, timezone
            started_at = datetime.fromisoformat(started_at_str)
            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
            if elapsed > settings.max_run_duration_seconds:
                logger.warning(
                    f"[routing] Run {run_id} exceeded maximum execution duration "
                    f"({elapsed:.1f}s > {settings.max_run_duration_seconds}s). Terminating repair cycle."
                )
                return "finalization_node"
        except Exception:
            pass

    # Repair needed condition
    current_attempts = state.get("repair_attempts", 0)
    max_attempts = state.get("max_repair_attempts", 3)

    if current_attempts < max_attempts:
        logger.info(
            f"[routing] Run {run_id} requires repair (attempt {current_attempts + 1} of {max_attempts}). "
            f"Routing back to coder_node."
        )
        return "coder_node"
    else:
        logger.warning(
            f"[routing] Run {run_id} reached maximum repair attempts ({max_attempts}). "
            f"Terminating repair cycle -> Finalizing."
        )
        return "finalization_node"
