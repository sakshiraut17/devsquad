"""Integration and security tests for Sub-Milestone 4: End-to-End Issue Dispatcher, Telemetry, and Hardened Human Gate."""

from unittest.mock import AsyncMock, MagicMock, patch as mock_patch
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.issue import Issue
from app.db.models.patch import Patch
from app.db.models.repository import Repository
from app.db.models.run import Run, RunStatus
from app.db.models.user import User
from app.orchestration import NodeDependencies, set_default_deps
from app.schemas.patch import PatchItem
from app.schemas.plan import PlanStep, StructuredPlan
from app.schemas.review import ReviewFinding, ReviewResponse
from app.schemas.test_result import TestResult
from app.services.github_service import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubBranchMetadata,
    GitHubIssue,
    GitHubRateLimitError,
    GitHubResourceNotFoundError,
)


@pytest.fixture
def mock_node_deps(test_db_session):
    planner = MagicMock()
    plan = StructuredPlan(
        objective="Dispatcher Integration Test Plan",
        problem_summary="Test problem",
        steps=[PlanStep(id="1", description="Step 1", target_files=["calculator.py"], rationale="Fix")],
        acceptance_criteria=["Works"],
        required_tests=["tests/test_calculator.py"],
        risks=[],
        assumptions=[],
        uncertainties=[],
        target_files=["calculator.py"],
        is_verified=True,
    )
    planner.plan = AsyncMock(return_value=plan)

    coder = MagicMock()
    patch_item = PatchItem(
        unified_diff="--- a/calculator.py\n+++ b/calculator.py\n@@ -1,1 +1,1 @@\n-old\n+new\n",
        target_files=["calculator.py"],
        base_commit_sha="commit-sha-4444",
        file_hashes={"calculator.py": "abc123hash"},
        summary="Dispatcher fix",
        revision=1,
        content_hash="dispatcherhash4444",
    )
    coder.generate_patch = AsyncMock(return_value=patch_item)

    tester = MagicMock()
    tester.run_tests = AsyncMock(return_value=TestResult(
        status="TESTS_PASSED",
        environment="isolated_container",
        commands_executed=["pytest -q"],
        exit_code=0,
        passed=3,
        failed=0,
        skipped=0,
        stdout="3 passed in 0.05s",
        stderr="",
        duration_ms=50,
    ))

    reviewer = MagicMock()
    reviewer.review = AsyncMock(return_value=ReviewResponse(
        findings=[],
        acceptance_criteria_met=True,
        recommendation="approve",
        unresolved_risks=[],
    ))

    deps = NodeDependencies(
        session_factory=lambda: test_db_session,
        planner_agent=planner,
        coder_agent=coder,
        tester_agent=tester,
        reviewer_agent=reviewer,
    )
    set_default_deps(deps)
    return deps


@pytest.mark.asyncio
async def test_github_remote_issues_authorized_and_unauthorized(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
):
    """Test retrieval of real/remote GitHub issues with authorization controls."""
    # 1. Create owned repo
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=10101,
        full_name="devsquad-org/telemetry-repo",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    # Mock GitHubService list_issues
    mock_gh_issues = [
        GitHubIssue(
            number=42,
            title="Division by zero bug",
            body="Crash occurs when dividing by zero",
            state="open",
            labels=["bug", "math"],
            html_url="https://github.com/devsquad-org/telemetry-repo/issues/42",
            author="alice",
            comments_count=2,
        )
    ]

    with mock_patch("app.services.github_service.GitHubService.list_issues", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_gh_issues
        with mock_patch.object(settings.github_token, "get_secret_value", return_value="ghp_test_token"):
            resp = await async_client.get(f"/api/v1/repositories/{repo.id}/github-issues")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["number"] == 42
            assert data[0]["title"] == "Division by zero bug"

    # Test unauthorized access by another user
    other_user = User(
        email="other@devsquad.ai",
        display_name="Other Developer",
        is_active=True,
    )
    test_db_session.add(other_user)
    await test_db_session.commit()

    from app.core.security import create_access_token
    other_token = create_access_token(user_id=other_user.id, email=other_user.email)
    unauth_resp = await async_client.get(
        f"/api/v1/repositories/{repo.id}/github-issues",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert unauth_resp.status_code == 403
    assert "Forbidden" in unauth_resp.json()["detail"]


@pytest.mark.asyncio
async def test_github_credentials_missing_reports_503(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
):
    """Test that missing GitHub credentials report 503 honestly without synthetic substitutions."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=20202,
        full_name="devsquad-org/no-creds-repo",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    with mock_patch.object(settings.github_token, "get_secret_value", return_value=""):
        resp = await async_client.get(f"/api/v1/repositories/{repo.id}/github-issues")
        assert resp.status_code == 503
        assert "DEVSQUAD_GITHUB_TOKEN missing" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_sync_github_issue_and_dispatch_run(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
    mock_node_deps,
):
    """Test importing an issue by number, creating run, and starting run with background support."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=30303,
        full_name="devsquad-org/dispatch-repo",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    mock_gh_issue = GitHubIssue(
        number=105,
        title="Negative indexing panic",
        body="Panic occurs on negative slice index",
        state="open",
        labels=["defect"],
        html_url="https://github.com/devsquad-org/dispatch-repo/issues/105",
        author="bob",
        comments_count=1,
    )

    with mock_patch("app.services.github_service.GitHubService.get_issue", new_callable=AsyncMock) as mock_get_issue:
        mock_get_issue.return_value = mock_gh_issue
        with mock_patch.object(settings.github_token, "get_secret_value", return_value="ghp_test_token"):
            # 1. Sync issue from GitHub
            sync_resp = await async_client.post(f"/api/v1/repositories/{repo.id}/sync-issue/105")
            assert sync_resp.status_code == 200
            issue_data = sync_resp.json()
            assert issue_data["github_issue_number"] == 105
            assert issue_data["title"] == "Negative indexing panic"
            issue_id = issue_data["id"]

            # 2. Dispatch / Create Run
            create_resp = await async_client.post(
                "/api/v1/runs",
                json={"repository_id": repo.id, "issue_id": issue_id},
            )
            assert create_resp.status_code == 201
            run_id = create_resp.json()["id"]

            # 3. Start Run with background=True
            start_resp = await async_client.post(
                f"/api/v1/runs/{run_id}/start?background=true",
                json={"metadata": {"is_test_fixture": True, "source_files": {"calculator.py": "def calc(): pass\n"}}},
            )
            assert start_resp.status_code == 200
            start_data = start_resp.json()
            assert start_data["background"] is True
            assert start_data["status"] == "PLANNING"


@pytest.mark.asyncio
async def test_enriched_workflow_state_endpoint(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
):
    """Test that GET /runs/{run_id}/state returns plan, test_result, and review data."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=40404,
        full_name="devsquad-org/state-repo",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="State test issue",
        body="Details",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status="AWAITING_APPROVAL",
        current_node="reviewer",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    mock_state_values = {
        "status": "AWAITING_APPROVAL",
        "current_stage": "finalizing",
        "patch_revision": 1,
        "repair_attempts": 0,
        "validation_status": "TESTS_PASSED",
        "plan": {
            "objective": "Enriched State Test",
            "problem_summary": "Summary",
            "steps": [],
            "acceptance_criteria": ["Criteria 1"],
            "required_tests": [],
            "risks": [],
            "assumptions": [],
            "uncertainties": [],
            "is_verified": True,
            "evidence_citations": [
                {
                    "file_path": "main.py",
                    "start_line": 1,
                    "end_line": 3,
                    "file_sha256": "abcdef",
                    "base_commit_sha": "commitsha",
                    "repo_owner": "devsquad-org",
                    "repo_name": "state-repo",
                    "excerpt": "def test():\n    pass",
                    "purpose": "PROBLEM_IDENTIFICATION",
                }
            ],
        },
        "test_result": {
            "status": "TESTS_PASSED",
            "environment": "isolated_container",
            "commands_executed": ["pytest"],
            "exit_code": 0,
            "passed": 5,
            "failed": 0,
            "skipped": 0,
            "stdout": "5 passed",
            "stderr": "",
            "duration_ms": 120,
        },
        "review": {
            "findings": [],
            "acceptance_criteria_met": True,
            "recommendation": "approve",
            "unresolved_risks": [],
        },
        "metadata": {
            "base_commit_sha": "commit-sha-40404",
            "repository_context": {
                "repo_owner": "devsquad-org",
                "repo_name": "state-repo",
                "target_branch": "main",
                "base_commit_sha": "commit-sha-40404",
                "truncation_applied": False,
            },
        },
    }

    with mock_patch("app.orchestration.get_orchestrator") as mock_get_orch:
        mock_orch = MagicMock()
        mock_orch.get_run_state = AsyncMock(return_value=mock_state_values)
        mock_get_orch.return_value = mock_orch

        resp = await async_client.get(f"/api/v1/runs/{run.id}/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checkpoint_found"] is True
        st = data["state"]
        assert st["plan"]["objective"] == "Enriched State Test"
        assert st["plan"]["is_verified"] is True
        assert len(st["plan"]["evidence_citations"]) == 1
        assert st["test_result"]["passed"] == 5
        assert st["review"]["recommendation"] == "approve"
        assert st["repository_context"]["base_commit_sha"] == "commit-sha-40404"


@pytest.mark.asyncio
async def test_approval_gate_blocks_on_blocking_reviewer_findings(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
):
    """Test that human approval is rejected when Reviewer reports blocking findings."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=50505,
        full_name="devsquad-org/approval-blocking-repo",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Security issue",
        body="Details",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status="AWAITING_APPROVAL",
        current_node="reviewer",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    patch_record = Patch(
        run_id=run.id,
        revision=1,
        unified_diff="--- a/sec.py\n+++ b/sec.py\n@@ -1,1 +1,1 @@\n-old\n+new\n",
        target_files=["sec.py"],
        summary="Fix vulnerability",
        content_hash="sechash12345",
        validation_status="TESTS_PASSED",
    )
    test_db_session.add(patch_record)
    await test_db_session.commit()

    mock_state_with_blocking_review = {
        "status": "AWAITING_APPROVAL",
        "review": {
            "findings": [
                {
                    "severity": "CRITICAL",
                    "file_path": "sec.py",
                    "line_number": 1,
                    "description": "SQL injection vulnerability detected in patch",
                }
            ],
            "acceptance_criteria_met": False,
            "recommendation": "reject",
            "unresolved_risks": ["High risk of data exfiltration"],
        },
    }

    with mock_patch("app.orchestration.get_orchestrator") as mock_get_orch:
        mock_orch = MagicMock()
        mock_orch.get_run_state = AsyncMock(return_value=mock_state_with_blocking_review)
        mock_get_orch.return_value = mock_orch

        # Attempting to approve must fail with 409
        resp = await async_client.post(
            f"/api/v1/runs/{run.id}/approve",
            json={
                "patch_id": patch_record.id,
                "decision": "approved",
                "patch_hash": patch_record.content_hash,
            },
        )
        assert resp.status_code == 409
        assert "blocking reviewer findings" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approval_gate_blocks_on_mismatched_base_commit_sha(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
):
    """Test that human approval is rejected when submitted base_commit_sha does not match run metadata."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=60606,
        full_name="devsquad-org/commit-mismatch-repo",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Commit issue",
        body="Details",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status="AWAITING_APPROVAL",
        current_node="reviewer",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    patch_record = Patch(
        run_id=run.id,
        revision=1,
        unified_diff="--- a/mod.py\n+++ b/mod.py\n@@ -1,1 +1,1 @@\n-old\n+new\n",
        target_files=["mod.py"],
        summary="Commit fix",
        content_hash="commithash123",
        validation_status="TESTS_PASSED",
    )
    test_db_session.add(patch_record)
    await test_db_session.commit()

    mock_state = {
        "status": "AWAITING_APPROVAL",
        "metadata": {"base_commit_sha": "actual-base-sha-1111"},
        "review": {"findings": [], "recommendation": "approve"},
    }

    with mock_patch("app.orchestration.get_orchestrator") as mock_get_orch:
        mock_orch = MagicMock()
        mock_orch.get_run_state = AsyncMock(return_value=mock_state)
        mock_get_orch.return_value = mock_orch

        # Submitting mismatched commit sha
        resp = await async_client.post(
            f"/api/v1/runs/{run.id}/approve",
            json={
                "patch_id": patch_record.id,
                "decision": "approved",
                "patch_hash": patch_record.content_hash,
                "base_commit_sha": "wrong-base-sha-9999",
            },
        )
        assert resp.status_code == 409
        assert "does not match run base commit SHA" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_explicit_rejection_audit_record_recording(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
):
    """Test that explicit rejection by a human maintainer succeeds and records feedback into audit trail."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=70707,
        full_name="devsquad-org/rejection-repo",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Rejection issue",
        body="Details",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status="AWAITING_APPROVAL",
        current_node="reviewer",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    patch_record = Patch(
        run_id=run.id,
        revision=1,
        unified_diff="--- a/rej.py\n+++ b/rej.py\n@@ -1,1 +1,1 @@\n-old\n+new\n",
        target_files=["rej.py"],
        summary="Patch to reject",
        content_hash="rejhash123",
        validation_status="FAILED",  # Even with failed validation, human maintainer must be allowed to reject!
    )
    test_db_session.add(patch_record)
    await test_db_session.commit()

    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={
            "patch_id": patch_record.id,
            "decision": "rejected",
            "patch_hash": patch_record.content_hash,
            "feedback": "Patch does not handle unicode edge cases properly.",
        },
    )
    assert resp.status_code == 200
    approval_data = resp.json()
    assert approval_data["decision"] == "rejected"
    assert approval_data["feedback"] == "Patch does not handle unicode edge cases properly."

    # Check that run status is now REJECTED
    await test_db_session.refresh(run)
    assert run.status == RunStatus.REJECTED.value
