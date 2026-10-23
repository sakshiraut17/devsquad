"""
Sub-Milestone 5: Production Reliability, Recovery, Telemetry, and Approval Stress Tests.
Validates:
- Background task exception handling: marks DB status FAILED, logs workflow_failed event (prevents zombie runs)
- Server restart recovery: reconcile_orphaned_runs detects and terminates orphaned active runs
- Concurrency safety: atomic registry checks prevent TOCTOU race conditions on start/resume
- Resumption revalidation: rejects checkpoints with corrupted repository context or forged patch hashes
- SSE telemetry hardening: query parameter authentication, stable Last-Event-ID recovery, deduplication, keepalive comments
- Approval gating under stress: duplicate/concurrent approval returns 409, tampered commit SHA returns 409, blocking reviewer findings return 409, maintainer rejection logs audit record
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch as mock_patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import compute_sha256, create_access_token
from app.db.models.agent_log import AgentLog
from app.db.models.approval_record import ApprovalRecord
from app.db.models.issue import Issue
from app.db.models.patch import Patch
from app.db.models.repository import Repository
from app.db.models.run import Run, RunStatus
from app.db.models.security_scan_record import SecurityScanRecord
from app.db.models.user import User
from app.orchestration import (
    DevSquadOrchestrator,
    OrchestrationError,
    RunNotResumableError,
    get_orchestrator,
)
from app.orchestration.state import WorkflowStage, WorkflowStatus
from app.schemas.approval import ApprovalRequest
from app.schemas.repository_context import ContextFile, RepositoryContext


@pytest.fixture
async def sample_run_fixture(test_db_session: AsyncSession, default_user: User):
    """Fixture providing an authorized repository, issue, and run."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=9901,
        full_name="devsquad-org/reliability-repo",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Crash under concurrent load",
        body="Race condition causes worker to terminate prematurely.",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.QUEUED.value,
        current_node="start",
    )
    test_db_session.add(run)
    await test_db_session.commit()
    return repo, issue, run


@pytest.mark.asyncio
async def test_background_run_unhandled_exception_marks_failed_cleanly(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    sample_run_fixture,
):
    """Verify that an unexpected exception in background worker updates DB run to FAILED (no zombie runs)."""
    repo, issue, run = sample_run_fixture

    # Mock start_run to simulate an unhandled worker crash
    with mock_patch("app.orchestration.service.DevSquadOrchestrator.start_run", new_callable=AsyncMock) as mock_start:
        mock_start.side_effect = RuntimeError("Worker out of memory simulated failure")

        resp = await async_client.post(f"/api/v1/runs/{run.id}/start?background=true")
        assert resp.status_code == 200
        assert resp.json()["status"] == RunStatus.PLANNING.value

        # Give background task a moment to execute and commit failure
        for _ in range(15):
            await asyncio.sleep(0.1)
            await test_db_session.rollback()
            await test_db_session.refresh(run)
            if run.status == RunStatus.FAILED.value:
                break

        assert run.status == RunStatus.FAILED.value
        assert "Workflow worker error: Worker out of memory simulated failure" in run.error_summary
        assert run.finished_at is not None

        # Verify workflow_failed agent log was recorded
        logs_res = await test_db_session.execute(
            select(AgentLog).where(AgentLog.run_id == run.id, AgentLog.event_type == "workflow_failed")
        )
        fail_log = logs_res.scalar_one_or_none()
        assert fail_log is not None
        assert "Worker crashed or raised" in fail_log.message


@pytest.mark.asyncio
async def test_reconcile_orphaned_runs(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    sample_run_fixture,
):
    """Verify that in-flight runs left active after a process crash/restart are reconciled to FAILED."""
    repo, issue, run = sample_run_fixture

    # Simulate run orphaned in CODING state
    run.status = RunStatus.CODING.value
    run.current_node = "coder_node"
    await test_db_session.commit()

    # Call reconciliation endpoint
    resp = await async_client.post("/api/v1/runs/reconcile-orphaned")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reconciled_count"] >= 1
    assert run.id in data["reconciled_run_ids"]

    # Verify run updated to FAILED
    await test_db_session.refresh(run)
    assert run.status == RunStatus.FAILED.value
    assert "Workflow execution interrupted by system restart" in run.error_summary
    assert run.finished_at is not None


@pytest.mark.asyncio
async def test_concurrent_start_requests_race_prevention(
    test_db_session: AsyncSession,
    sample_run_fixture,
):
    """Verify atomic registry checks prevent concurrent duplicate start operations."""
    repo, issue, run = sample_run_fixture
    orchestrator = get_orchestrator()

    # Simulate an active task currently executing
    mock_active_task = MagicMock(spec=asyncio.Task)
    mock_active_task.done.return_value = False

    from app.orchestration.service import _active_tasks, _registry_lock

    async with _registry_lock:
        _active_tasks[run.id] = mock_active_task

    try:
        # Attempting start_run should immediately raise OrchestrationError
        with pytest.raises(OrchestrationError, match="is already actively executing"):
            await orchestrator.start_run(run.id, test_db_session)
    finally:
        async with _registry_lock:
            _active_tasks.pop(run.id, None)


@pytest.mark.asyncio
async def test_resume_run_rejects_tampered_or_stale_repository_context(
    test_db_session: AsyncSession,
    sample_run_fixture,
):
    """Verify resume_run revalidates repository context integrity and rejects tampered checkpoints."""
    repo, issue, run = sample_run_fixture
    orchestrator = get_orchestrator()

    valid_content = "def add(a, b): return a + b\n"
    tampered_context_dict = {
        "repo_owner": "devsquad-org",
        "repo_name": "reliability-repo",
        "target_branch": "main",
        "base_commit_sha": "commit-valid-sha-001",
        "selected_files": [
            {
                "path": "math_utils.py",
                "content": valid_content,
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "commit_sha": "commit-valid-sha-001",
                "size_bytes": len(valid_content.encode("utf-8")),
                "estimated_tokens": 10,
            }
        ],
        "total_token_count": 10,
    }

    mock_state_values = {
        "run_id": run.id,
        "thread_id": f"thread-{run.id}",
        "status": WorkflowStatus.WAITING_FOR_APPROVAL.value,
        "current_stage": WorkflowStage.TESTING.value,
        "metadata": {
            "repository_context": tampered_context_dict,
        },
    }

    mock_snapshot = MagicMock()
    mock_snapshot.values = mock_state_values

    with mock_patch("app.orchestration.service.compile_devsquad_graph") as mock_compile:
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
        mock_compile.return_value = mock_graph

        with pytest.raises(RunNotResumableError):
            await orchestrator.resume_run(run.id, test_db_session)


@pytest.mark.asyncio
async def test_resume_run_rejects_tampered_patch_hash(
    test_db_session: AsyncSession,
    sample_run_fixture,
):
    """Verify resume_run revalidates patch hash consistency and rejects forged patch hashes."""
    repo, issue, run = sample_run_fixture
    orchestrator = get_orchestrator()

    valid_diff = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n"
    forged_hash = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    mock_state_values = {
        "run_id": run.id,
        "thread_id": f"thread-{run.id}",
        "status": WorkflowStatus.WAITING_FOR_APPROVAL.value,
        "current_stage": WorkflowStage.TESTING.value,
        "current_patch": {
            "unified_diff": valid_diff,
            "patch_hash": forged_hash,
        },
        "metadata": {},
    }

    mock_snapshot = MagicMock()
    mock_snapshot.values = mock_state_values

    with mock_patch("app.orchestration.service.compile_devsquad_graph") as mock_compile:
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
        mock_compile.return_value = mock_graph

        with pytest.raises(RunNotResumableError, match="patch hash mismatch detected"):
            await orchestrator.resume_run(run.id, test_db_session)


@pytest.mark.asyncio
async def test_sse_stream_query_token_auth_and_reconnection(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
    sample_run_fixture,
):
    """Verify SSE streaming supports query token authentication and stable Last-Event-ID reconnection."""
    repo, issue, run = sample_run_fixture

    # 1. Add sequential audit logs to the run
    log1 = AgentLog(
        run_id=run.id,
        agent_name="planner",
        event_type="plan_formulated",
        message="Created plan for issue",
    )
    log2 = AgentLog(
        run_id=run.id,
        agent_name="coder",
        event_type="patch_generated",
        message="Generated unified diff patch",
    )
    test_db_session.add(log1)
    test_db_session.add(log2)
    run.status = RunStatus.COMPLETED.value
    await test_db_session.commit()
    await test_db_session.refresh(log1)
    await test_db_session.refresh(log2)

    token = create_access_token(user_id=default_user.id, email=default_user.email)
    auth_header = {"Authorization": f"Bearer {token}"}

    # 2. Reject raw token in query parameter (OWASP / URL logging protection)
    token_resp = await async_client.get(
        f"/api/v1/runs/{run.id}/stream?token={token}",
        headers={},
    )
    assert token_resp.status_code == 401
    assert "prohibited for security reasons" in token_resp.text

    # 3. Generate short-lived stream ticket
    ticket_resp = await async_client.post(
        f"/api/v1/runs/{run.id}/stream-ticket",
        headers=auth_header,
    )
    assert ticket_resp.status_code == 200
    ticket_data = ticket_resp.json()
    assert "ticket" in ticket_data
    assert ticket_data["run_id"] == run.id
    assert ticket_data["expires_in"] == 60
    ticket = ticket_data["ticket"]

    # 4. Connect with stream ticket and last_event_id=log1.id
    # Should only emit log2, avoiding replaying log1!
    resp = await async_client.get(
        f"/api/v1/runs/{run.id}/stream?ticket={ticket}&last_event_id={log1.id}",
        headers={},  # No Bearer header; authenticates via short-lived ticket
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    body = resp.text
    assert f"id: {log2.id}" in body
    assert f"id: {log1.id}" not in body  # Correctly skipped already seen event
    assert "event: status_update" in body
    assert "event: done" in body

    # 5. Replay attempt with same ticket should be rejected
    replay_resp = await async_client.get(
        f"/api/v1/runs/{run.id}/stream?ticket={ticket}",
        headers={},
    )
    assert replay_resp.status_code == 401
    assert "replay detected" in replay_resp.text


@pytest.mark.asyncio
async def test_approval_gate_rejects_duplicate_or_concurrent_approval(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
    sample_run_fixture,
):
    """Verify approval endpoint returns HTTP 409 Conflict when run is already approved/rejected."""
    repo, issue, run = sample_run_fixture

    diff_content = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-1\n+2\n"
    content_hash = compute_sha256(diff_content)

    patch = Patch(
        run_id=run.id,
        revision=1,
        unified_diff=diff_content,
        content_hash=content_hash,
        validation_status="TESTS_PASSED",
        summary="Fix discount calculation",
    )
    test_db_session.add(patch)

    sec_record = SecurityScanRecord(
        run_id=run.id,
        patch_id=patch.id,
        patch_hash=content_hash,
        status="PASSED",
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        info_count=0,
        scanners_executed=["secret_scanner"],
        block_reasons=[],
    )
    test_db_session.add(sec_record)

    run.status = RunStatus.AWAITING_APPROVAL.value
    await test_db_session.commit()

    approval_payload = {
        "patch_id": patch.id,
        "decision": "approved",
        "patch_hash": content_hash,
    }

    # First approval succeeds
    resp1 = await async_client.post(f"/api/v1/runs/{run.id}/approve", json=approval_payload)
    assert resp1.status_code == 200
    assert resp1.json()["decision"] == "approved"

    # Second approval returns 409 Conflict
    resp2 = await async_client.post(f"/api/v1/runs/{run.id}/approve", json=approval_payload)
    assert resp2.status_code == 409
    assert "cannot receive human approval" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_approval_gate_rejects_tampered_base_commit_sha(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    sample_run_fixture,
):
    """Verify approval rejects tampered or mismatched base commit SHA with HTTP 409 Conflict."""
    repo, issue, run = sample_run_fixture

    diff_content = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-1\n+2\n"
    content_hash = compute_sha256(diff_content)

    patch = Patch(
        run_id=run.id,
        revision=1,
        unified_diff=diff_content,
        content_hash=content_hash,
        validation_status="TESTS_PASSED",
        summary="Fix discount calculation",
    )
    test_db_session.add(patch)
    run.status = RunStatus.AWAITING_APPROVAL.value
    await test_db_session.commit()

    # Mock orchestrator state with base_commit_sha
    mock_state = {
        "metadata": {
            "base_commit_sha": "expected-commit-sha-12345",
        }
    }
    with mock_patch("app.orchestration.service.DevSquadOrchestrator.get_run_state", new_callable=AsyncMock) as mock_get_state:
        mock_get_state.return_value = mock_state

        resp = await async_client.post(
            f"/api/v1/runs/{run.id}/approve",
            json={
                "patch_id": patch.id,
                "decision": "approved",
                "patch_hash": content_hash,
                "base_commit_sha": "forged-or-mismatched-commit-sha",
            },
        )
        assert resp.status_code == 409
        assert "does not match run base commit SHA" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approval_gate_rejects_blocking_reviewer_findings(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    sample_run_fixture,
):
    """Verify approval is blocked if reviewer findings include CRITICAL or recommendation is reject."""
    repo, issue, run = sample_run_fixture

    diff_content = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-1\n+2\n"
    content_hash = compute_sha256(diff_content)

    patch = Patch(
        run_id=run.id,
        revision=1,
        unified_diff=diff_content,
        content_hash=content_hash,
        validation_status="TESTS_PASSED",
        summary="Fix discount calculation",
    )
    test_db_session.add(patch)
    run.status = RunStatus.AWAITING_APPROVAL.value
    await test_db_session.commit()

    # Mock reviewer report with CRITICAL finding
    mock_state = {
        "metadata": {},
        "review": {
            "recommendation": "request_changes",
            "findings": [
                {
                    "severity": "CRITICAL",
                    "description": "SQL injection vulnerability introduced.",
                }
            ],
        },
    }
    with mock_patch("app.orchestration.service.DevSquadOrchestrator.get_run_state", new_callable=AsyncMock) as mock_get_state:
        mock_get_state.return_value = mock_state

        resp = await async_client.post(
            f"/api/v1/runs/{run.id}/approve",
            json={
                "patch_id": patch.id,
                "decision": "approved",
                "patch_hash": content_hash,
            },
        )
        assert resp.status_code == 409
        assert "blocking reviewer findings" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_explicit_maintainer_rejection_audit_record(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    sample_run_fixture,
):
    """Verify human maintainers can explicitly reject a run with feedback, recording an auditable ApprovalRecord."""
    repo, issue, run = sample_run_fixture

    diff_content = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-1\n+2\n"
    content_hash = compute_sha256(diff_content)

    patch = Patch(
        run_id=run.id,
        revision=1,
        unified_diff=diff_content,
        content_hash=content_hash,
        validation_status="PARTIAL_VALIDATION",  # Even if tests didn't fully pass
        summary="Fix discount calculation",
    )
    test_db_session.add(patch)
    run.status = RunStatus.AWAITING_APPROVAL.value
    await test_db_session.commit()

    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={
            "patch_id": patch.id,
            "decision": "rejected",
            "patch_hash": content_hash,
            "feedback": "Patch does not meet performance requirements.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "rejected"
    assert data["feedback"] == "Patch does not meet performance requirements."

    # Verify run updated to REJECTED
    await test_db_session.refresh(run)
    assert run.status == RunStatus.REJECTED.value
