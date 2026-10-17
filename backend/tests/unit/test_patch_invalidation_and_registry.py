"""Unit and regression tests for patch invalidation, evidence binding, and anti-repetition registry."""
import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.config import settings
from app.db.models.patch import Patch
from app.db.models.run import Run, RunStatus
from app.db.models.user import User
from app.db.models.repository import Repository
from app.db.models.issue import Issue
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.orchestration.nodes import (
    coder_node,
    finalization_node,
    reviewer_node,
    sandbox_tester_node,
    set_default_deps,
    NodeDependencies,
)
from app.orchestration.routing import route_after_reviewer
from app.orchestration.state import DevSquadState, WorkflowStatus, create_initial_state
from app.schemas.approval import ApprovalRequest
from app.schemas.patch import PatchItem
from app.schemas.repair_registry import FailedPatchEntry, FailedPatchRegistry
from app.schemas.review import ReviewFinding, ReviewResponse
from app.schemas.test_result import TestResult
from app.services.agents.diff_utils import (
    canonicalize_unified_diff,
    compute_canonical_patch_hash,
    compute_canonical_patch_id,
)

BASE_SHA_A = "1111111111111111111111111111111111111111"
BASE_SHA_B = "2222222222222222222222222222222222222222"

VALID_PLAN_DICT = {
    "objective": "Fix addition bug",
    "problem_summary": "Bug in add function causing incorrect calculation",
    "steps": [
        {
            "id": "s1",
            "description": "Fix add implementation",
            "target_files": ["math.py"],
            "dependencies": [],
            "rationale": "Correct subtraction operator to addition",
        }
    ],
    "acceptance_criteria": ["add(1, 2) returns 3"],
    "required_tests": ["tests/test_math.py"],
    "risks": [],
    "uncertainties": [],
    "assumptions": [],
}


DIFF_A = (
    "--- a/math.py\n"
    "+++ b/math.py\n"
    "@@ -1,2 +1,2 @@\n"
    "-def add(a, b): return a - b\n"
    "+def add(a, b): return a + b\n"
)

DIFF_B = (
    "--- a/math.py\n"
    "+++ b/math.py\n"
    "@@ -1,2 +1,3 @@\n"
    "+# added docstring\n"
    " def add(a, b): return a + b\n"
)


# --- 7. Patch normalization and canonical hash stability ---
def test_canonical_patch_hash_stability():
    """Verify that different line endings and trailing whitespace produce the exact same canonical hash."""
    diff_crlf = DIFF_A.replace("\n", "\r\n")
    diff_trailing_spaces = "\n".join(line + "   " for line in DIFF_A.split("\n"))
    diff_padded = f"\n\n{DIFF_A}\n\n\n"

    hash_clean = compute_canonical_patch_hash(DIFF_A)
    hash_crlf = compute_canonical_patch_hash(diff_crlf)
    hash_trailing = compute_canonical_patch_hash(diff_trailing_spaces)
    hash_padded = compute_canonical_patch_hash(diff_padded)

    assert hash_clean == hash_crlf
    assert hash_clean == hash_trailing
    assert hash_clean == hash_padded
    assert compute_canonical_patch_id(BASE_SHA_A, DIFF_A) == f"{BASE_SHA_A}:{hash_clean}"


# --- 1. Patch A passes validation, then changes to patch B ---
@pytest.mark.asyncio
async def test_patch_change_atomically_invalidates_validation_evidence():
    """When patch changes from A to B in coder_node, validation evidence for A is wiped."""
    hash_a = compute_canonical_patch_hash(DIFF_A)
    patch_a = {
        "id": "patch-a",
        "unified_diff": DIFF_A,
        "target_files": ["math.py"],
        "base_commit_sha": BASE_SHA_A,
        "content_hash": hash_a,
        "revision": 1,
        "summary": "Fix math add",
    }
    stale_test_result = {
        "status": "TESTS_PASSED",
        "environment": "docker_container",
        "patch_hash": hash_a,
        "base_commit_sha": BASE_SHA_A,
        "patch_revision": 1,
    }
    stale_review = {
        "recommendation": "approve",
        "acceptance_criteria_met": True,
        "findings": [],
        "unresolved_risks": [],
        "patch_hash": hash_a,
        "patch_revision": 1,
    }

    state = create_initial_state(run_id="run-inv-1", repository_id="repo-1", issue_id="issue-1")
    state["plan"] = dict(VALID_PLAN_DICT)
    state["current_patch"] = patch_a
    state["patch_revision"] = 1
    state["test_result"] = stale_test_result
    state["review_result"] = stale_review
    state["validation_status"] = "TESTS_PASSED"
    state["approval_status"] = "PENDING"
    state["metadata"] = {"source_files": {"math.py": "def add(a, b): return a - b\n"}, "base_commit_sha": BASE_SHA_A}

    # Mock coder agent returning patch B
    mock_coder = MagicMock()
    hash_b = compute_canonical_patch_hash(DIFF_B)
    patch_item_b = PatchItem(
        unified_diff=DIFF_B,
        target_files=["math.py"],
        base_commit_sha=BASE_SHA_A,
        summary="Revision 2 patch B",
        revision=2,
        content_hash=hash_b,
    )
    mock_coder.generate_patch = AsyncMock(return_value=patch_item_b)

    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock()
    deps = NodeDependencies(session_factory=lambda: mock_ctx, coder_agent=mock_coder)
    set_default_deps(deps)

    result = await coder_node(state)

    # Invariants verification: dependent evidence for patch A MUST be invalidated to None
    assert result["current_patch"]["content_hash"] == hash_b
    assert result["patch_revision"] == 2
    assert result["test_result"] is None
    assert result["review_result"] is None
    assert result["validation_status"] == "PENDING_VALIDATION"
    assert result["approval_status"] == "PENDING"
    assert result["repair_feedback"] is None


# --- 2. Patch A is reviewed, then changes to patch B ---
@pytest.mark.asyncio
async def test_stale_validation_or_review_rejected_at_finalization():
    """Finalization node rejects runs where test or review evidence does not match the active patch hash."""
    hash_a = compute_canonical_patch_hash(DIFF_A)
    hash_b = compute_canonical_patch_hash(DIFF_B)

    # State has patch B, but test result refers to patch A
    state: DevSquadState = {
        "run_id": "run-mismatch-1",
        "status": WorkflowStatus.RUNNING.value,
        "plan": {"objective": "Fix", "steps": []},
        "current_patch": {
            "unified_diff": DIFF_B,
            "content_hash": hash_b,
            "base_commit_sha": BASE_SHA_A,
            "revision": 2,
        },
        "test_result": {
            "status": "TESTS_PASSED",
            "patch_hash": hash_a,  # Stale!
            "base_commit_sha": BASE_SHA_A,
            "patch_revision": 1,
        },
        "review_result": {
            "recommendation": "approve",
            "findings": [],
            "patch_hash": hash_b,
        },
        "metadata": {"base_commit_sha": BASE_SHA_A},
    }

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock()
    deps = NodeDependencies(session_factory=lambda: mock_ctx)
    set_default_deps(deps)

    res = await finalization_node(state)
    assert res["status"] == WorkflowStatus.FAILED.value
    assert "Stale validation evidence" in res["error_message"]


# --- 3. Human approval exists for patch A, then patch B is generated ---
@pytest.mark.asyncio
async def test_approval_rejects_superseded_or_stale_patch(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Approval endpoint rejects approving an older patch revision or unvalidated patch."""
    repo = Repository(
        id="repo-approval-test",
        owner_id=default_user.id,
        github_repository_id=9999,
        full_name="testuser/repo-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-approval-test",
        repository_id=repo.id,
        github_issue_number=10,
        title="Test issue",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-approval-test",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
    )
    test_db_session.add(run)
    await test_db_session.commit()

    hash_a = compute_canonical_patch_hash(DIFF_A)
    hash_b = compute_canonical_patch_hash(DIFF_B)

    patch_a = Patch(
        id="patch-rev-1",
        run_id=run.id,
        revision=1,
        unified_diff=DIFF_A,
        target_files=["math.py"],
        summary="Rev 1",
        content_hash=hash_a,
        validation_status="TESTS_PASSED",
    )
    patch_b = Patch(
        id="patch-rev-2",
        run_id=run.id,
        revision=2,
        unified_diff=DIFF_B,
        target_files=["math.py"],
        summary="Rev 2",
        content_hash=hash_b,
        validation_status="PENDING_VALIDATION",
    )
    test_db_session.add_all([patch_a, patch_b])
    await test_db_session.commit()

    # 1. Attempt to approve superseded Patch A -> 409 Conflict
    resp_a = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={"patch_id": patch_a.id, "decision": "approved", "patch_hash": hash_a},
    )
    assert resp_a.status_code == 409
    assert "superseded by newer revision" in resp_a.json()["detail"]

    # 2. Attempt to approve Patch B while validation is PENDING -> 409 Conflict
    resp_b = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={"patch_id": patch_b.id, "decision": "approved", "patch_hash": hash_b},
    )
    assert resp_b.status_code == 409
    assert "ineligible for approval" in resp_b.json()["detail"]


# --- 4. Identical failed patch generated repeatedly ---
def test_anti_repetition_registry_detects_duplicate_failure():
    """Anti-repetition registry catches identical failing patch within same run and base revision."""
    registry = FailedPatchRegistry()
    hash_a = compute_canonical_patch_hash(DIFF_A)

    registry.record_failure(
        run_id="run-dup-1",
        repository_id="repo-1",
        base_commit_sha=BASE_SHA_A,
        patch_hash=hash_a,
        revision=1,
        failure_category="TEST_FAILED",
        diagnostic_fingerprint="AssertionError: 2 != 3",
        validation_environment="docker_container",
    )

    dup = registry.is_duplicate_failed_patch(
        run_id="run-dup-1",
        base_commit_sha=BASE_SHA_A,
        patch_hash=hash_a,
        environment="docker_container",
    )
    assert dup is not None
    assert dup.revision == 1
    assert dup.failure_category == "TEST_FAILED"


# --- 5. Identical patch encountered in a different run ---
def test_anti_repetition_registry_permits_different_run():
    """Identical patch hash in an unrelated run is NOT blocked."""
    registry = FailedPatchRegistry()
    hash_a = compute_canonical_patch_hash(DIFF_A)

    registry.record_failure(
        run_id="run-1",
        repository_id="repo-1",
        base_commit_sha=BASE_SHA_A,
        patch_hash=hash_a,
        revision=1,
        failure_category="TEST_FAILED",
        diagnostic_fingerprint="AssertionError",
    )

    # Same patch in run-2 must not be treated as a duplicate of run-1
    dup = registry.is_duplicate_failed_patch(
        run_id="run-2",
        base_commit_sha=BASE_SHA_A,
        patch_hash=hash_a,
    )
    assert dup is None


# --- 6. Identical patch against a different base revision ---
def test_anti_repetition_registry_permits_different_base_revision():
    """Identical patch diff against a different base commit SHA is not blocked."""
    registry = FailedPatchRegistry()
    hash_a = compute_canonical_patch_hash(DIFF_A)

    registry.record_failure(
        run_id="run-1",
        repository_id="repo-1",
        base_commit_sha=BASE_SHA_A,
        patch_hash=hash_a,
        revision=1,
        failure_category="TEST_FAILED",
        diagnostic_fingerprint="AssertionError",
    )

    # Against BASE_SHA_B, circumstances are distinct
    dup = registry.is_duplicate_failed_patch(
        run_id="run-1",
        base_commit_sha=BASE_SHA_B,
        patch_hash=hash_a,
    )
    assert dup is None


# --- 8. Stale validation arriving after a newer patch is recorded ---
@pytest.mark.asyncio
async def test_reviewer_node_rejects_stale_validation_evidence():
    """Reviewer agent node fails-fast when test evidence does not match current patch hash."""
    hash_a = compute_canonical_patch_hash(DIFF_A)
    hash_b = compute_canonical_patch_hash(DIFF_B)

    state: DevSquadState = {
        "run_id": "run-stale-rev",
        "plan": dict(VALID_PLAN_DICT),
        "current_patch": {
            "unified_diff": DIFF_B,
            "content_hash": hash_b,
            "target_files": ["math.py"],
            "base_commit_sha": BASE_SHA_A,
            "revision": 2,
            "summary": "Rev 2",
        },
        "test_result": {
            "status": "TESTS_PASSED",
            "environment": "docker_container",
            "patch_hash": hash_a,  # Stale!
            "base_commit_sha": BASE_SHA_A,
            "patch_revision": 1,
        },
        "metadata": {"base_commit_sha": BASE_SHA_A, "source_files": {}},
    }

    mock_reviewer = MagicMock()
    deps = NodeDependencies(reviewer_agent=mock_reviewer)
    set_default_deps(deps)

    res = await reviewer_node(state)
    assert res["status"] == WorkflowStatus.FAILED.value
    assert res["error_code"] == "STALE_VALIDATION_EVIDENCE"
    # Reviewer LLM must never be called on stale evidence
    mock_reviewer.review.assert_not_called()


# --- 9. Concurrent repair and validation state transitions ---
def test_create_initial_state_and_invariants():
    """Initial state enforces clean defaults and empty failed patch registry."""
    state = create_initial_state(run_id="run-init", repository_id="repo-1", issue_id="issue-1")
    assert state["patch_revision"] == 0
    assert state["repair_attempts"] == 0
    assert state["test_result"] is None
    assert state["review_result"] is None
    assert state["validation_status"] == "NOT_STARTED"
    assert state["failed_patch_registry"] == []


# --- 10. Process restart and repair-budget persistence ---
def test_failed_patch_registry_serialization_survives_checkpoint_roundtrip():
    """FailedPatchRegistry survives Pydantic serialization roundtrip cleanly."""
    registry = FailedPatchRegistry()
    registry.record_failure(
        run_id="run-persist-1",
        repository_id="repo-1",
        base_commit_sha=BASE_SHA_A,
        patch_hash=compute_canonical_patch_hash(DIFF_A),
        revision=1,
        failure_category="TEST_FAILED",
        diagnostic_fingerprint="SyntaxError at line 4",
        validation_environment="docker_container",
        details={"custom_key": "custom_val"},
    )

    serialized = registry.model_dump()
    recovered = FailedPatchRegistry.model_validate(serialized)
    assert len(recovered.entries) == 1
    assert recovered.entries[0].run_id == "run-persist-1"
    assert recovered.entries[0].failure_category == "TEST_FAILED"
    assert recovered.entries[0].details["custom_key"] == "custom_val"


# --- 11. Cancellation during repair ---
@pytest.mark.asyncio
async def test_cancellation_during_repair_halts_coder():
    """Coder node immediately exits without executing if status is CANCELLED."""
    state = create_initial_state(run_id="run-cancel", repository_id="repo-1", issue_id="issue-1")
    state["status"] = WorkflowStatus.CANCELLED.value
    state["error_message"] = "User aborted."

    mock_coder = MagicMock()
    deps = NodeDependencies(coder_agent=mock_coder)
    set_default_deps(deps)

    res = await coder_node(state)
    assert res["status"] == WorkflowStatus.CANCELLED.value
    assert res["current_stage"] == "FINALIZING"
    mock_coder.generate_patch.assert_not_called()


# --- 12. Maximum repair attempts and timeout ---
def test_route_after_reviewer_bounds_repairs_and_detects_timeout():
    """Routing terminates repair cycle when max_repair_attempts is reached or duration exceeded."""
    # 1. Max retries exceeded
    state: DevSquadState = {
        "run_id": "run-bounds-1",
        "status": WorkflowStatus.RUNNING.value,
        "repair_attempts": 3,
        "max_repair_attempts": 3,
        "test_result": {"status": "TESTS_FAILED"},
        "review_result": {"recommendation": "request_changes", "findings": []},
    }
    assert route_after_reviewer(state) == "finalization_node"

    # 2. Within retries
    state["repair_attempts"] = 1
    assert route_after_reviewer(state) == "coder_node"

    # 3. Timeout exceeded
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=settings.max_run_duration_seconds + 100)).isoformat()
    state["started_at"] = old_time
    assert route_after_reviewer(state) == "finalization_node"
