"""Integration tests for Phase 4.5 preview API endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.models.approval_record import ApprovalRecord
from app.db.models.issue import Issue
from app.db.models.patch import Patch
from app.db.models.repository import Repository
from app.db.models.run import Run, RunStatus
from app.db.models.user import User


@pytest.mark.asyncio
async def test_auth_session_and_me(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    """Test creating session and retrieving current user profile."""
    # 1. Create a session
    resp = await async_client.post(
        "/api/v1/auth/session",
        json={"email": "lead@devsquad.ai", "display_name": "Lead Engineer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "lead@devsquad.ai"
    assert data["user"]["display_name"] == "Lead Engineer"

    token = data["access_token"]

    # 2. Query /me with token
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "lead@devsquad.ai"
    assert me_data["is_active"] is True


@pytest.mark.asyncio
async def test_overview_stats(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
) -> None:
    """Test real aggregated overview stats endpoint."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=98765,
        full_name="devsquad/preview-repo",
        default_branch="main",
        is_active=True,
    )
    test_db_session.add(repo)
    await test_db_session.flush()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Sample Issue",
        body="Sample issue description",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.flush()

    run = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="awaiting_approval",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    resp = await async_client.get("/api/v1/overview/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["repositories_count"] >= 1
    assert stats["open_issues_count"] >= 1
    assert stats["total_runs_count"] >= 1
    assert stats["awaiting_approval_count"] >= 1


@pytest.mark.asyncio
async def test_get_repository_and_issue_by_id(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
) -> None:
    """Test retrieving repository and issue by unique IDs."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=55443,
        full_name="devsquad/detail-test",
        default_branch="main",
        is_active=True,
    )
    test_db_session.add(repo)
    await test_db_session.flush()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=10,
        title="Detail Issue",
        body="Detailed body",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    # Repos
    r_resp = await async_client.get(f"/api/v1/repositories/{repo.id}")
    assert r_resp.status_code == 200
    assert r_resp.json()["full_name"] == "devsquad/detail-test"

    r_404 = await async_client.get("/api/v1/repositories/non-existent-id")
    assert r_404.status_code == 404

    # Issues
    i_resp = await async_client.get(f"/api/v1/issues/{issue.id}")
    assert i_resp.status_code == 200
    assert i_resp.json()["title"] == "Detail Issue"

    i_404 = await async_client.get("/api/v1/issues/non-existent-id")
    assert i_404.status_code == 404


@pytest.mark.asyncio
async def test_get_run_patches_and_approvals(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
) -> None:
    """Test retrieving patches and approval records for a run."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=99001,
        full_name="devsquad/patch-test",
        default_branch="main",
        is_active=True,
    )
    test_db_session.add(repo)
    await test_db_session.flush()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=42,
        title="Patch Issue",
        body="Body",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.flush()

    run = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.APPROVED.value,
        current_node="end",
    )
    test_db_session.add(run)
    await test_db_session.flush()

    patch = Patch(
        run_id=run.id,
        revision=1,
        unified_diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n",
        target_files=["file.py"],
        summary="Fixed line",
        content_hash="abc123canonicalhash",
        validation_status="passed",
    )
    test_db_session.add(patch)
    await test_db_session.flush()

    approval = ApprovalRecord(
        run_id=run.id,
        patch_id=patch.id,
        approver_id=default_user.id,
        decision="approved",
        patch_hash=patch.content_hash,
        validation_evidence={"status": "passed"},
    )
    test_db_session.add(approval)
    await test_db_session.commit()

    # Patches
    p_resp = await async_client.get(f"/api/v1/runs/{run.id}/patches")
    assert p_resp.status_code == 200
    patches = p_resp.json()
    assert len(patches) == 1
    assert patches[0]["revision"] == 1
    assert patches[0]["summary"] == "Fixed line"
    assert patches[0]["content_hash"] == "abc123canonicalhash"

    # Approvals
    a_resp = await async_client.get(f"/api/v1/runs/{run.id}/approvals")
    assert a_resp.status_code == 200
    approvals = a_resp.json()
    assert len(approvals) == 1
    assert approvals[0]["decision"] == "approved"
    assert approvals[0]["patch_hash"] == "abc123canonicalhash"
