"""Integration tests for run orchestration REST API endpoints."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.issue import Issue
from app.db.models.repository import Repository
from app.db.models.run import Run
from app.db.models.user import User
from app.orchestration import NodeDependencies, set_default_deps
from app.schemas.patch import PatchItem
from app.schemas.plan import PlanStep, StructuredPlan
from app.schemas.review import ReviewFinding, ReviewResponse
from app.schemas.test_result import TestResult


@pytest.fixture
def mock_node_deps(test_db_session):
    planner = MagicMock()
    plan = StructuredPlan(
        objective="API Run Test Plan",
        problem_summary="Summary",
        steps=[PlanStep(id="1", description="Step 1", target_files=["main.py"], rationale="Fix")],
        acceptance_criteria=["Works"],
        required_tests=["tests/test_main.py"],
        risks=[],
        assumptions=[],
        uncertainties=[],
    )
    planner.plan = AsyncMock(return_value=plan)

    coder = MagicMock()
    patch = PatchItem(
        unified_diff="--- a/main.py\n+++ b/main.py\n@@ -1,1 +1,1 @@\n-old\n+new\n",
        target_files=["main.py"],
        base_commit_sha="commitsha",
        file_hashes={"main.py": "hash"},
        summary="API patch",
        revision=1,
        content_hash="apihash123",
    )
    coder.generate_patch = AsyncMock(return_value=patch)

    tester = MagicMock()
    tester.run_tests = AsyncMock(return_value=TestResult(
        status="PARTIAL_VALIDATION",
        environment="host_ast_fallback",
        commands_executed=["ast.parse"],
        exit_code=0,
        passed=1,
        failed=0,
        skipped=0,
        stdout="AST valid",
        stderr="",
        duration_ms=10,
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
async def test_runs_orchestration_api_endpoints(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
    mock_node_deps,
):
    # 1. Create Repo, Issue, Run for default_user
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=7777,
        full_name="devsquad/api-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="API issue",
        body="Details",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    # Create run via API
    create_resp = await async_client.post(
        "/api/v1/runs",
        json={"repository_id": repo.id, "issue_id": issue.id},
    )
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    # 2. Start Run via API
    start_resp = await async_client.post(
        f"/api/v1/runs/{run_id}/start",
        json={"metadata": {"source_files": {"main.py": "old\n"}, "is_test_fixture": True}},
    )
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "WAITING_FOR_APPROVAL"
    assert start_data["patch_revision"] == 1

    # 3. Get State via API
    state_resp = await async_client.get(f"/api/v1/runs/{run_id}/state")
    assert state_resp.status_code == 200
    state_data = state_resp.json()
    assert state_data["run_id"] == run_id

    # 4. Get Events via API
    events_resp = await async_client.get(f"/api/v1/runs/{run_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 4
    event_names = [e["event_type"] for e in events]
    assert "workflow_started" in event_names
    assert "workflow_finalized" in event_names

    # 5. Cancel Run via API
    # Create another run to cancel
    run2 = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status="RUNNING",
        current_node="coder",
    )
    test_db_session.add(run2)
    await test_db_session.commit()

    cancel_resp = await async_client.post(
        f"/api/v1/runs/{run2.id}/cancel",
        json={"reason": "User cancelled via UI"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    # 6. Error handling for non-existent runs
    bad_start = await async_client.post("/api/v1/runs/non-existent-id/start")
    assert bad_start.status_code == 404

    bad_cancel = await async_client.post("/api/v1/runs/non-existent-id/cancel")
    assert bad_cancel.status_code == 404

    bad_state = await async_client.get("/api/v1/runs/non-existent-id/state")
    assert bad_state.status_code == 404

    bad_events = await async_client.get("/api/v1/runs/non-existent-id/events")
    assert bad_events.status_code == 404

