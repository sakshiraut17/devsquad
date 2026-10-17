"""End-to-end integration tests verifying complete workflow lifecycles from repository context to human approval."""
import tempfile
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentLog,
    ApprovalRecord,
    Issue,
    Patch,
    Repository,
    Run,
    RunStatus,
    User,
)
from app.orchestration import (
    DevSquadOrchestrator,
    NodeDependencies,
    WorkflowStatus,
    set_default_deps,
)
from app.schemas.patch import PatchItem
from app.schemas.plan import PlanStep, StructuredPlan
from app.schemas.review import ReviewFinding, ReviewResponse
from app.schemas.test_result import TestResult
from app.core.security import compute_sha256 as compute_patch_hash


@pytest.mark.asyncio
async def test_end_to_end_realistic_workflow_to_human_approval(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """
    Simulate full realistic workflow:
    1. Context Preparation (realistic repository fixture with bug)
    2. Planner Agent generates structured fix plan
    3. Coder Agent produces verified minimal patch
    4. Sandbox Tester Agent runs tests dynamically
    5. Independent Reviewer Agent inspects changes
    6. Workflow safely transitions to AWAITING_APPROVAL
    7. Human maintainer inspects and cryptographically approves via API
    8. Audit trail and immutable ApprovalRecord are verified
    """
    # 1. Setup Repository & Issue owned by default_user
    repo = Repository(
        id="repo-e2e-001",
        owner_id=default_user.id,
        github_repository_id=5001,
        full_name="devsquad/math-toolkit",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-e2e-001",
        repository_id=repo.id,
        github_issue_number=101,
        title="calculate_average returns incorrect result due to off-by-one denominator",
        body="calculate_average([10, 20, 30]) returns 30.0 instead of 20.0 due to len(nums) - 1 division.",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    # 2. Setup initial source files for the repository
    initial_math_code = (
        "def calculate_average(nums):\n"
        "    if not nums:\n"
        "        return 0.0\n"
        "    return sum(nums) / (len(nums) - 1)\n"
    )
    test_code = (
        "from calculator.math import calculate_average\n\n"
        "def test_calculate_average():\n"
        "    assert calculate_average([10, 20, 30]) == 20.0\n"
    )

    source_files = {
        "calculator/math.py": initial_math_code,
        "tests/test_math.py": test_code,
    }

    # 3. Create Run entity via API or DB
    create_resp = await async_client.post(
        "/api/v1/runs",
        json={"repository_id": repo.id, "issue_id": issue.id},
    )
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    # 4. Configure Agents
    planner = MagicMock()
    plan = StructuredPlan(
        objective="Fix off-by-one division in calculate_average",
        problem_summary="Denominator uses len(nums) - 1 instead of len(nums)",
        steps=[
            PlanStep(
                id="S1",
                description="Change denominator to len(nums)",
                target_files=["calculator/math.py"],
                rationale="Divisor must be sample count",
            )
        ],
        acceptance_criteria=["calculate_average([10, 20, 30]) returns 20.0"],
        required_tests=["tests/test_math.py"],
        risks=[],
        assumptions=[],
        uncertainties=[],
    )
    planner.plan = AsyncMock(return_value=plan)

    diff_content = (
        "--- a/calculator/math.py\n"
        "+++ b/calculator/math.py\n"
        "@@ -4,1 +4,1 @@\n"
        "-    return sum(nums) / (len(nums) - 1)\n"
        "+    return sum(nums) / len(nums)\n"
    )
    expected_patch_hash = compute_patch_hash(diff_content)

    coder = MagicMock()
    patch = PatchItem(
        unified_diff=diff_content,
        target_files=["calculator/math.py"],
        base_commit_sha="base-commit-sha-9999",
        file_hashes={"calculator/math.py": "initialhash"},
        summary="Fix denominator off-by-one in calculate_average",
        revision=1,
        content_hash=expected_patch_hash,
    )
    coder.generate_patch = AsyncMock(return_value=patch)

    tester = MagicMock()
    test_res = TestResult(
        status="TESTS_PASSED",
        environment="docker",
        commands_executed=["pytest tests/test_math.py"],
        exit_code=0,
        passed=1,
        failed=0,
        skipped=0,
        stdout="tests/test_math.py . [100%]\n1 passed in 0.05s",
        stderr="",
        duration_ms=50,
        patch_hash=expected_patch_hash,
        patch_revision=1,
        base_commit_sha="base-commit-sha-9999",
    )
    tester.run_tests = AsyncMock(return_value=test_res)

    reviewer = MagicMock()
    rev_res = ReviewResponse(
        findings=[
            ReviewFinding(
                id="RV-1",
                severity="INFO",
                category="correctness",
                file_path="calculator/math.py",
                line_number=4,
                description="Off-by-one correctly resolved with zero division guard preserved",
                evidence="return sum(nums) / len(nums)",
                recommendation="Approve change",
            )
        ],
        acceptance_criteria_met=True,
        recommendation="approve",
        unresolved_risks=[],
    )
    reviewer.review = AsyncMock(return_value=rev_res)

    deps = NodeDependencies(
        session_factory=lambda: test_db_session,
        planner_agent=planner,
        coder_agent=coder,
        tester_agent=tester,
        reviewer_agent=reviewer,
    )
    set_default_deps(deps)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        chk_db = tmp.name

    orchestrator = DevSquadOrchestrator(checkpoint_db_path=chk_db)

    # 5. Execute Start Run
    final_state = await orchestrator.start_run(
        run_id=run_id,
        db=test_db_session,
        metadata={
            "source_files": source_files,
            "base_commit_sha": "base-commit-sha-9999",
            "is_test_fixture": True,
        },
    )

    # 6. Verify State Reached WAITING_FOR_APPROVAL
    assert final_state["status"] == WorkflowStatus.WAITING_FOR_APPROVAL.value
    assert final_state["patch_revision"] == 1
    assert final_state["current_patch"]["content_hash"] == expected_patch_hash

    # Verify DB Run Status
    db_run = await test_db_session.get(Run, run_id)
    assert db_run.status == RunStatus.AWAITING_APPROVAL.value

    # Verify Persisted Patch
    patch_res = await test_db_session.execute(
        select(Patch).where(Patch.run_id == run_id)
    )
    patches = patch_res.scalars().all()
    assert len(patches) == 1
    persisted_patch = patches[0]
    assert persisted_patch.content_hash == expected_patch_hash
    assert persisted_patch.validation_status in ("TESTS_PASSED", "VALIDATED")

    # 7. Maintainer Approves via Authenticated API
    approve_resp = await async_client.post(
        f"/api/v1/runs/{run_id}/approve",
        json={
            "patch_id": persisted_patch.id,
            "decision": "approved",
            "patch_hash": expected_patch_hash,
            "feedback": "Approved for pull request creation. Fix is minimal and tests passed.",
        },
    )
    assert approve_resp.status_code == 200
    approval_body = approve_resp.json()
    assert approval_body["decision"] == "approved"
    assert approval_body["patch_hash"] == expected_patch_hash

    # 8. Verify DB Final State & Immutable Audit Record
    await test_db_session.refresh(db_run)
    assert db_run.status == RunStatus.APPROVED.value

    approvals_res = await test_db_session.execute(
        select(ApprovalRecord).where(ApprovalRecord.run_id == run_id)
    )
    approvals = approvals_res.scalars().all()
    assert len(approvals) == 1
    assert approvals[0].patch_id == persisted_patch.id
    assert approvals[0].patch_hash == expected_patch_hash
    assert approvals[0].approver_id == default_user.id
    assert "Fix is minimal" in approvals[0].feedback

    # Verify Audit Logs
    logs_res = await test_db_session.execute(
        select(AgentLog).where(AgentLog.run_id == run_id)
    )
    event_types = [l.event_type for l in logs_res.scalars().all()]
    assert "workflow_started" in event_types
    assert "plan_generated" in event_types
    assert "patch_created" in event_types
    assert "tests_executed" in event_types
    assert "review_completed" in event_types
    assert "workflow_finalized" in event_types


@pytest.mark.asyncio
async def test_failing_tests_prevent_approval_transition(
    test_db_session: AsyncSession,
    default_user: User,
    mock_agents,
):
    """
    Ensure fail-closed safety gate:
    If dynamic sandbox tests fail, the workflow must NEVER transition to WAITING_FOR_APPROVAL
    even if an LLM reviewer mistakenly suggests 'approve'.
    """
    planner, coder, tester, reviewer = mock_agents

    # Tester reports failure
    failed_test_res = TestResult(
        status="FAILED",
        environment="docker",
        commands_executed=["pytest tests/test_math.py"],
        exit_code=1,
        passed=0,
        failed=1,
        skipped=0,
        stdout="FAILED tests/test_math.py::test_calculate_average - AssertionError",
        stderr="Test failure",
        duration_ms=45,
    )
    tester.run_tests = AsyncMock(return_value=failed_test_res)

    # Reviewer incorrectly attempts to approve despite failing tests
    flawed_review = ReviewResponse(
        findings=[],
        acceptance_criteria_met=True,
        recommendation="approve",  # Reviewer errantly approves
        unresolved_risks=[],
    )
    reviewer.review = AsyncMock(return_value=flawed_review)

    deps = NodeDependencies(
        session_factory=lambda: test_db_session,
        planner_agent=planner,
        coder_agent=coder,
        tester_agent=tester,
        reviewer_agent=reviewer,
    )
    set_default_deps(deps)

    repo = Repository(
        id="repo-fail-gate",
        owner_id=default_user.id,
        github_repository_id=5002,
        full_name="devsquad/failing-tests-gate",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-fail-gate",
        repository_id=repo.id,
        github_issue_number=102,
        title="Failing test safety gate test",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-fail-gate",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.QUEUED.value,
        current_node="start",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        chk_db = tmp.name

    orchestrator = DevSquadOrchestrator(checkpoint_db_path=chk_db)

    final_state = await orchestrator.start_run(
        run_id=run.id,
        db=test_db_session,
        metadata={
            "source_files": {"calc.py": "return 1\n"},
            "is_test_fixture": True,
        },
    )

    # Gate must NOT allow WAITING_FOR_APPROVAL
    assert final_state["status"] != WorkflowStatus.WAITING_FOR_APPROVAL.value
    assert final_state["status"] == WorkflowStatus.FAILED.value
    assert "tests failed" in (final_state.get("error_message") or "").lower()

    db_run = await test_db_session.get(Run, run.id)
    assert db_run.status == RunStatus.FAILED.value
    assert db_run.status != RunStatus.AWAITING_APPROVAL.value
