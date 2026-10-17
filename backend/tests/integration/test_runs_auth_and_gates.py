"""Integration tests for Runs API Authentication, Authorization, and Fail-Closed Routing Gates."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    ApprovalRecord,
    Issue,
    Patch,
    Repository,
    Run,
    RunStatus,
    User,
)
from app.orchestration import WorkflowStatus
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_unauthenticated_requests_fail_with_401(
    unauthenticated_client: AsyncClient,
):
    """Ensure all /runs endpoints strictly reject requests without valid credentials."""
    # List runs
    resp = await unauthenticated_client.get("/api/v1/runs")
    assert resp.status_code == 401

    # Create run
    resp = await unauthenticated_client.post(
        "/api/v1/runs",
        json={"repository_id": "rep-1", "issue_id": "iss-1"},
    )
    assert resp.status_code == 401

    # Get run
    resp = await unauthenticated_client.get("/api/v1/runs/dummy-id")
    assert resp.status_code == 401

    # Start run
    resp = await unauthenticated_client.post("/api/v1/runs/dummy-id/start")
    assert resp.status_code == 401

    # Approve run
    resp = await unauthenticated_client.post(
        "/api/v1/runs/dummy-id/approve",
        json={
            "patch_id": "dummy-patch-id",
            "decision": "approved",
            "patch_hash": "hash123",
        },
    )
    assert resp.status_code == 401

    # Cancel run
    resp = await unauthenticated_client.post("/api/v1/runs/dummy-id/cancel")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cross_user_forbidden_access_403(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Ensure User B cannot view, start, or approve Runs belonging to User A's repository."""
    # User A (victim / another user)
    user_a = User(
        id="00000000-0000-0000-0000-000000000002",
        email="user_a@devsquad.ai",
        display_name="User A",
        is_active=True,
    )
    test_db_session.add(user_a)
    await test_db_session.commit()

    repo_a = Repository(
        id="repo-user-a",
        owner_id=user_a.id,
        github_repository_id=9001,
        full_name="usera/private-project",
        default_branch="main",
    )
    test_db_session.add(repo_a)
    await test_db_session.commit()

    issue_a = Issue(
        id="issue-user-a",
        repository_id=repo_a.id,
        github_issue_number=42,
        title="Secured Issue",
        state="open",
    )
    test_db_session.add(issue_a)
    await test_db_session.commit()

    run_a = Run(
        id="run-user-a",
        repository_id=repo_a.id,
        issue_id=issue_a.id,
        status=RunStatus.QUEUED.value,
        current_node="start",
    )
    test_db_session.add(run_a)
    await test_db_session.commit()

    # async_client is authenticated as default_user (User B)
    # 1. Attempt to create run on User A's repo -> 403
    create_resp = await async_client.post(
        "/api/v1/runs",
        json={"repository_id": repo_a.id, "issue_id": issue_a.id},
    )
    assert create_resp.status_code == 403
    assert "Forbidden" in create_resp.json()["detail"]

    # 2. Attempt to read User A's run -> 403
    get_resp = await async_client.get(f"/api/v1/runs/{run_a.id}")
    assert get_resp.status_code == 403

    # 3. Attempt to start User A's run -> 403
    start_resp = await async_client.post(f"/api/v1/runs/{run_a.id}/start")
    assert start_resp.status_code == 403

    # 4. Attempt to approve User A's run -> 403
    approve_resp = await async_client.post(
        f"/api/v1/runs/{run_a.id}/approve",
        json={
            "patch_id": "dummy-patch-id",
            "decision": "approved",
            "patch_hash": "dummyhash",
        },
    )
    assert approve_resp.status_code == 403


@pytest.mark.asyncio
async def test_tamper_evident_approval_verification(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Verify cryptographic anti-tamper patch check and audit trail creation on approval."""
    # Setup repo and run owned by default_user
    repo = Repository(
        id="repo-tamper-test",
        owner_id=default_user.id,
        github_repository_id=9002,
        full_name="devsquad/tamper-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-tamper-test",
        repository_id=repo.id,
        github_issue_number=10,
        title="Tamper verification issue",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-tamper-test",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="reviewer",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    genuine_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    patch = Patch(
        id="patch-tamper-test",
        run_id=run.id,
        revision=1,
        unified_diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n",
        target_files=["file.py"],
        summary="Safe update",
        content_hash=genuine_hash,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch)
    await test_db_session.commit()

    # 1. Tampered hash payload -> Must be rejected with 409 Conflict
    tampered_resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={
            "patch_id": patch.id,
            "decision": "approved",
            "patch_hash": "forged_malicious_hash_value_9999999",
            "feedback": "Looks good to me but hash is wrong",
        },
    )
    assert tampered_resp.status_code == 409
    assert "does not match" in tampered_resp.json()["detail"]

    # Verify run status is still AWAITING_APPROVAL
    await test_db_session.refresh(run)
    assert run.status == RunStatus.AWAITING_APPROVAL.value

    # 2. Legitimate hash payload -> Approved with Audit Trail
    legit_resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={
            "patch_id": patch.id,
            "decision": "approved",
            "patch_hash": genuine_hash,
            "feedback": "Approved for production merge after security review",
        },
    )
    assert legit_resp.status_code == 200
    approval_data = legit_resp.json()
    assert approval_data["decision"] == "approved"
    assert approval_data["approver_id"] == default_user.id
    assert approval_data["patch_hash"] == genuine_hash
    assert approval_data["feedback"] == "Approved for production merge after security review"

    # Verify Database Run Status updated to APPROVED
    await test_db_session.refresh(run)
    assert run.status == RunStatus.APPROVED.value

    # Verify Database ApprovalRecord existence
    records_res = await test_db_session.execute(
        select(ApprovalRecord).where(ApprovalRecord.run_id == run.id)
    )
    records = records_res.scalars().all()
    assert len(records) == 1
    assert records[0].decision == "approved"
    assert records[0].patch_hash == genuine_hash
    assert records[0].feedback == "Approved for production merge after security review"


@pytest.mark.asyncio
async def test_approval_rejected_if_run_not_awaiting_approval(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Approval endpoint must reject attempts to approve runs not in AWAITING_APPROVAL state."""
    repo = Repository(
        id="repo-state-test",
        owner_id=default_user.id,
        github_repository_id=9003,
        full_name="devsquad/state-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-state-test",
        repository_id=repo.id,
        github_issue_number=11,
        title="State test",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-not-ready",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.TESTING.value,
        current_node="tester",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={
            "patch_id": "dummy-patch-id",
            "decision": "approved",
            "patch_hash": "somehash",
        },
    )
    assert resp.status_code == 400
    assert "cannot receive human approval" in resp.json()["detail"].lower()
