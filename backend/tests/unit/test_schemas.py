"""Unit tests for Pydantic V2 schemas validation."""
import pytest
from pydantic import ValidationError
from app.schemas.approval import ApprovalRequest
from app.schemas.patch import PatchItem
from app.schemas.plan import PlanStep, StructuredPlan
from app.schemas.repository import RepositoryCreate
from app.schemas.review import ReviewFinding, ReviewResponse
from app.schemas.test_result import TestResult


def test_structured_plan_valid():
    step = PlanStep(
        id="step-1",
        description="Fix authentication bug in auth.py",
        target_files=["app/auth.py"],
        dependencies=[],
        rationale="Token validation logic is inverted",
    )
    plan = StructuredPlan(
        objective="Fix auth logic",
        problem_summary="Users cannot login",
        steps=[step],
        acceptance_criteria=["Valid tokens return 200"],
        required_tests=["tests/test_auth.py"],
        risks=["Session invalidation"],
        assumptions=["Tokens are JWT"],
    )
    assert len(plan.steps) == 1
    assert plan.steps[0].id == "step-1"


def test_structured_plan_rejects_empty_steps_or_criteria():
    with pytest.raises(ValidationError):
        StructuredPlan(
            objective="Empty plan",
            problem_summary="Problem",
            steps=[],  # min_length=1
            acceptance_criteria=["Criterion"],
            required_tests=[],
        )

    with pytest.raises(ValidationError):
        StructuredPlan(
            objective="Empty criteria",
            problem_summary="Problem",
            steps=[PlanStep(id="1", description="desc", rationale="rat")],
            acceptance_criteria=[],  # min_length=1
            required_tests=[],
        )


def test_plan_step_forbids_extra_fields():
    with pytest.raises(ValidationError):
        PlanStep(
            id="1",
            description="desc",
            rationale="rat",
            unauthorized_field="malicious_payload",
        )


def test_patch_item_valid():
    patch = PatchItem(
        unified_diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new",
        target_files=["file.py"],
        base_commit_sha="a" * 40,
        file_hashes={"file.py": "b" * 64},
        summary="Updated line in file.py",
        revision=1,
        content_hash="c" * 64,
    )
    assert patch.revision == 1
    assert len(patch.target_files) == 1


def test_review_finding_severity_validation():
    valid_finding = ReviewFinding(
        id="FIND-1",
        severity="HIGH",
        category="security",
        description="SQL injection vulnerability",
        evidence="f'SELECT * FROM users WHERE id = {user_id}'",
        recommendation="Use parameterized query",
    )
    assert valid_finding.severity == "HIGH"

    with pytest.raises(ValidationError):
        ReviewFinding(
            id="FIND-2",
            severity="SUPER_CRITICAL",  # Invalid severity literal
            category="security",
            description="desc",
            evidence="ev",
            recommendation="rec",
        )


def test_approval_request_validation():
    req = ApprovalRequest(
        patch_id="patch-123",
        decision="approved",
        patch_hash="a" * 64,
        feedback="Looks good to me",
    )
    assert req.decision == "approved"

    with pytest.raises(ValidationError):
        ApprovalRequest(
            patch_id="patch-123",
            decision="maybe",  # Invalid decision
            patch_hash="a" * 64,
        )


def test_repository_create_name_validation():
    valid = RepositoryCreate(
        github_repository_id=12345,
        full_name="devsquad-org/devsquad",
    )
    assert valid.full_name == "devsquad-org/devsquad"

    with pytest.raises(ValidationError):
        RepositoryCreate(
            github_repository_id=12345,
            full_name="invalid-repo-name-without-owner",
        )
