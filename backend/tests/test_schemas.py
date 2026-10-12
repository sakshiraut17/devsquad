from datetime import datetime, timezone
from app.schemas.repository import RepositoryResponse, IssueResponse, FileTreeNode, FileContentResponse
from app.schemas.workflow import (
    StructuredPlan,
    PlanStep,
    PlanResponse,
    PatchItem,
    PatchResponse,
    ValidationResult,
    ReviewFinding,
    ReviewResponse,
    RunStatusResponse,
)


def test_repository_schemas():
    """Verify repository schemas validate correctly."""
    repo = RepositoryResponse(
        full_name="octocat/Hello-World",
        default_branch="main",
        is_active=True,
        stars_count=100,
        open_issues_count=5,
    )
    assert repo.full_name == "octocat/Hello-World"
    assert repo.default_branch == "main"

    issue = IssueResponse(
        issue_number=1,
        title="Test Bug",
        body="Details",
        state="open",
    )
    assert issue.issue_number == 1
    assert issue.state == "open"

    node = FileTreeNode(path="app/main.py", type="blob", size=1024)
    assert node.path == "app/main.py"
    assert node.type == "blob"

    content = FileContentResponse(path="README.md", content="# Hello", size=7)
    assert content.path == "README.md"
    assert content.content == "# Hello"


def test_workflow_schemas():
    """Verify workflow schemas validate correctly."""
    step = PlanStep(step_number=1, title="Step 1", description="Do task", target_files=["main.py"])
    plan = StructuredPlan(
        objective="Fix crash",
        affected_files=["main.py"],
        steps=[step],
        risks=["Minimal"],
        acceptance_criteria=["Zero error"],
    )
    assert plan.objective == "Fix crash"
    assert len(plan.steps) == 1

    patch = PatchItem(target_file="main.py", unified_diff="--- a\n+++ b", explanation="Fixed bug")
    assert patch.target_file == "main.py"

    validation = ValidationResult(
        run_id="run-1",
        exit_code=0,
        stdout="Passed",
        stderr="",
        duration_ms=150,
        passed=True,
        executed_in_docker=False,
    )
    assert validation.passed is True

    finding = ReviewFinding(severity="info", file="main.py", line=10, message="LGTM")
    review = ReviewResponse(
        run_id="run-1",
        passed=True,
        findings=[finding],
        summary="Looks great",
        approved_for_pr=True,
    )
    assert review.approved_for_pr is True

    status = RunStatusResponse(
        id="run-1",
        repository_full_name="octocat/Hello-World",
        issue_number=1,
        status="completed",
        current_node="completed",
        started_at=datetime.now(timezone.utc),
        plan=plan,
        patches=[patch],
        test_results=validation,
        review=review,
    )
    assert status.id == "run-1"
    assert status.status == "completed"
