"""Integration tests for DevSquadOrchestrator service execution, recovery, and cancellation."""

import tempfile
import os
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_log import AgentLog
from app.db.models.issue import Issue
from app.db.models.patch import Patch
from app.db.models.repository import Repository
from app.db.models.run import Run, RunStatus
from app.db.models.user import User
from app.orchestration import (
    DevSquadOrchestrator,
    NodeDependencies,
    RunNotResumableError,
    WorkflowStatus,
    set_default_deps,
)
from app.schemas.patch import PatchItem
from app.schemas.plan import PlanStep, StructuredPlan
from app.schemas.review import ReviewFinding, ReviewResponse
from app.schemas.test_result import TestResult


@pytest.fixture
def mock_agents():
    planner = MagicMock()
    plan = StructuredPlan(
        objective="Fix math bug",
        problem_summary="Subtract bug",
        steps=[PlanStep(id="1", description="Fix op", target_files=["calc.py"], rationale="Fix")],
        acceptance_criteria=["calc works"],
        required_tests=["tests/test_calc.py"],
        risks=[],
        assumptions=[],
        uncertainties=[],
    )
    planner.plan = AsyncMock(return_value=plan)

    coder = MagicMock()
    patch = PatchItem(
        unified_diff="--- a/calc.py\n+++ b/calc.py\n@@ -1,1 +1,1 @@\n-a+b\n+a-b\n",
        target_files=["calc.py"],
        base_commit_sha="sha123",
        file_hashes={"calc.py": "hash1"},
        summary="Fix subtraction",
        revision=1,
        content_hash="contenthash123",
    )
    coder.generate_patch = AsyncMock(return_value=patch)

    tester = MagicMock()
    test_res = TestResult(
        status="PARTIAL_VALIDATION",
        environment="host_ast_fallback",
        commands_executed=["ast.parse"],
        exit_code=0,
        passed=1,
        failed=0,
        skipped=0,
        stdout="AST passed",
        stderr="",
        duration_ms=15,
    )
    tester.run_tests = AsyncMock(return_value=test_res)

    reviewer = MagicMock()
    rev_res = ReviewResponse(
        findings=[ReviewFinding(
            id="F1",
            severity="INFO",
            category="style",
            file_path="calc.py",
            line_number=1,
            description="Clean code",
            evidence="looks good",
            recommendation="keep",
        )],
        acceptance_criteria_met=True,
        recommendation="approve",
        unresolved_risks=[],
    )
    reviewer.review = AsyncMock(return_value=rev_res)

    return planner, coder, tester, reviewer


@pytest.mark.asyncio
async def test_orchestrator_full_run_lifecycle(test_db_session: AsyncSession, mock_agents):
    planner, coder, tester, reviewer = mock_agents

    # Inject mock dependencies
    deps = NodeDependencies(
        session_factory=lambda: test_db_session,
        planner_agent=planner,
        coder_agent=coder,
        tester_agent=tester,
        reviewer_agent=reviewer,
    )
    set_default_deps(deps)

    # 1. Setup DB records
    user = User(email="architect@example.com", display_name="Architect")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(
        owner_id=user.id,
        github_repository_id=8888,
        full_name="devsquad/orchestrator-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Test issue",
        body="Details",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-orch-001",
        repository_id=repo.id,
        issue_id=issue.id,
        status="QUEUED",
        current_node="start",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        chk_db = tmp.name

    try:
        orchestrator = DevSquadOrchestrator(checkpoint_db_path=chk_db)

        # 2. Start Run
        final_state = await orchestrator.start_run(
            run_id="run-orch-001",
            db=test_db_session,
            metadata={"source_files": {"calc.py": "a+b\n"}, "is_test_fixture": True},
        )

        assert final_state["status"] == WorkflowStatus.WAITING_FOR_APPROVAL.value
        assert final_state["patch_revision"] == 1
        assert final_state["plan"] is not None

        # 3. Verify Database Entities Updated
        db_run = await test_db_session.get(Run, "run-orch-001")
        assert db_run.status == RunStatus.AWAITING_APPROVAL.value
        assert db_run.finished_at is not None

        # Verify Patch Entity
        patches_res = await test_db_session.execute(
            select(Patch).where(Patch.run_id == "run-orch-001")
        )
        patches = patches_res.scalars().all()
        assert len(patches) == 1
        assert patches[0].revision == 1
        assert patches[0].content_hash == "contenthash123"

        # Verify AgentLogs
        logs_res = await test_db_session.execute(
            select(AgentLog).where(AgentLog.run_id == "run-orch-001")
        )
        logs = logs_res.scalars().all()
        event_types = [l.event_type for l in logs]
        assert "workflow_started" in event_types
        assert "plan_generated" in event_types
        assert "patch_created" in event_types
        assert "tests_executed" in event_types
        assert "review_completed" in event_types
        assert "workflow_finalized" in event_types

        # 4. Verify Checkpointer Snapshot
        saved_state = await orchestrator.get_run_state("run-orch-001")
        assert saved_state is not None
        assert saved_state["run_id"] == "run-orch-001"
    finally:
        if os.path.exists(chk_db):
            try:
                os.remove(chk_db)
            except OSError:
                pass


@pytest.mark.asyncio
async def test_orchestrator_cancel_run(test_db_session: AsyncSession):
    user = User(email="cancel@example.com", display_name="Canceler")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(
        owner_id=user.id,
        github_repository_id=8889,
        full_name="devsquad/cancel-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=2,
        title="Cancel issue",
        body="Details",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-cancel-002",
        repository_id=repo.id,
        issue_id=issue.id,
        status="RUNNING",
        current_node="coder",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    orchestrator = DevSquadOrchestrator(checkpoint_db_path=":memory:")
    state = await orchestrator.cancel_run("run-cancel-002", db=test_db_session, reason="User clicked cancel")

    assert state["status"] == WorkflowStatus.CANCELLED.value
    db_run = await test_db_session.get(Run, "run-cancel-002")
    assert db_run.status == RunStatus.CANCELLED.value
    assert "User clicked cancel" in db_run.error_summary


@pytest.mark.asyncio
async def test_orchestrator_resume_terminal_run_raises(test_db_session: AsyncSession):
    user = User(email="term@example.com", display_name="Term")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(
        owner_id=user.id,
        github_repository_id=8890,
        full_name="devsquad/term-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=3,
        title="Term issue",
        body="Details",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    # Completed run cannot be resumed
    run = Run(
        id="run-term-003",
        repository_id=repo.id,
        issue_id=issue.id,
        status="COMPLETED",
        current_node="finalization",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    orchestrator = DevSquadOrchestrator(checkpoint_db_path=":memory:")
    with pytest.raises(RunNotResumableError):
        await orchestrator.resume_run("run-term-003", db=test_db_session)


@pytest.mark.asyncio
async def test_orchestrator_start_run_errors(test_db_session: AsyncSession):
    orchestrator = DevSquadOrchestrator(checkpoint_db_path=":memory:")
    from app.orchestration.exceptions import OrchestrationError

    # 1. Non-existent run
    with pytest.raises(OrchestrationError) as exc1:
        await orchestrator.start_run("non-existent-run", db=test_db_session)
    assert "not found in database" in str(exc1.value)

    # 2. Terminal run cannot be started
    user = User(email="term2@example.com", display_name="Term2")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(owner_id=user.id, github_repository_id=8891, full_name="devsquad/term2", default_branch="main")
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(repository_id=repo.id, github_issue_number=4, title="Term2 issue", state="open")
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(id="run-term2-004", repository_id=repo.id, issue_id=issue.id, status="COMPLETED")
    test_db_session.add(run)
    await test_db_session.commit()

    with pytest.raises(OrchestrationError) as exc2:
        await orchestrator.start_run("run-term2-004", db=test_db_session)
    assert "terminal state" in str(exc2.value)


@pytest.mark.asyncio
async def test_orchestrator_cancel_and_resume_not_found(test_db_session: AsyncSession):
    orchestrator = DevSquadOrchestrator(checkpoint_db_path=":memory:")
    from app.orchestration.exceptions import OrchestrationError

    # Cancel non-existent
    with pytest.raises(OrchestrationError):
        await orchestrator.cancel_run("does-not-exist", db=test_db_session)

    # Resume non-existent
    with pytest.raises(OrchestrationError):
        await orchestrator.resume_run("does-not-exist", db=test_db_session)

    # State for non-existent returns None
    state = await orchestrator.get_run_state("does-not-exist")
    assert state is None

