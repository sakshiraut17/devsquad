"""Unit tests for ReviewerAgent."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.schemas.patch import PatchItem
from app.schemas.plan import PlanStep, StructuredPlan
from app.schemas.review import ReviewFinding, ReviewResponse
from app.schemas.test_result import TestResult
from app.services.agents.reviewer import ReviewerAgent
from app.services.llm.base import LLMResponse, LLMUsage


@pytest.fixture
def sample_plan():
    return StructuredPlan(
        objective="Fix math subtraction error",
        problem_summary="subtract function returns addition",
        steps=[PlanStep(id="1", description="Fix op", target_files=["math.py"], rationale="Fix")],
        acceptance_criteria=["subtract(5, 3) == 2"],
        required_tests=["tests/test_math.py"],
        risks=[],
        assumptions=[],
        uncertainties=[],
    )


@pytest.fixture
def sample_patch():
    return PatchItem(
        unified_diff="--- a/math.py\n+++ b/math.py\n@@ -1,1 +1,1 @@\n-a + b\n+a - b\n",
        target_files=["math.py"],
        base_commit_sha="commit123",
        file_hashes={"math.py": "hash1"},
        summary="Fix subtraction operator",
        revision=1,
        content_hash="contenthash1",
    )


@pytest.fixture
def sample_test_result():
    return TestResult(
        status="PARTIAL_VALIDATION",
        environment="host_ast_fallback",
        commands_executed=["ast.parse"],
        exit_code=0,
        passed=1,
        failed=0,
        skipped=0,
        stdout="AST passed",
        stderr="",
        duration_ms=10,
        security_limitations=["Docker unavailable"],
    )


@pytest.mark.asyncio
async def test_reviewer_agent_approves_clean_patch(sample_plan, sample_patch, sample_test_result):
    expected_review = ReviewResponse(
        findings=[
            ReviewFinding(
                id="FIND-001",
                severity="INFO",
                category="style",
                file_path="math.py",
                line_number=1,
                description="Clean change",
                evidence="a - b replaces a + b",
                potential_impact="None",
                recommendation="Looks good",
            )
        ],
        acceptance_criteria_met=True,
        recommendation="approve",
        unresolved_risks=[],
    )

    mock_provider = MagicMock()
    mock_provider.generate_structured = AsyncMock(
        return_value=LLMResponse(
            data=expected_review,
            raw_response="{}",
            provider="gemini",
            model="gemini-2.0-flash",
            usage=LLMUsage(latency_ms=100.0, prompt_tokens=80, completion_tokens=40, total_tokens=120),
        )
    )

    reviewer = ReviewerAgent(llm_provider=mock_provider)
    result = await reviewer.review(
        issue_title="Bug in subtraction",
        issue_body="5 - 3 was giving 8",
        plan=sample_plan,
        patch=sample_patch,
        test_result=sample_test_result,
        source_files={"math.py": "a + b\n"},
    )

    assert result.acceptance_criteria_met is True
    assert result.recommendation == "approve"
    assert len(result.findings) == 1
    # Check that because test_result was PARTIAL_VALIDATION, sandbox note was added to unresolved_risks
    assert any("Docker sandbox was unavailable" in risk for risk in result.unresolved_risks)


@pytest.mark.asyncio
async def test_reviewer_agent_overrides_approve_on_critical_finding(sample_plan, sample_patch, sample_test_result):
    # LLM erroneously recommended "approve" despite reporting a CRITICAL security vulnerability
    bad_review = ReviewResponse(
        findings=[
            ReviewFinding(
                id="FIND-CRIT-1",
                severity="CRITICAL",
                category="security",
                file_path="math.py",
                line_number=1,
                description="Remote code execution via eval",
                evidence="eval(user_input)",
                potential_impact="Arbitrary command execution",
                recommendation="Do not use eval",
            )
        ],
        acceptance_criteria_met=False,
        recommendation="approve",  # Erroneous recommendation
        unresolved_risks=[],
    )

    mock_provider = MagicMock()
    mock_provider.generate_structured = AsyncMock(
        return_value=LLMResponse(
            data=bad_review,
            raw_response="{}",
            provider="gemini",
            model="gemini-2.0-flash",
            usage=LLMUsage(latency_ms=100.0, prompt_tokens=80, completion_tokens=40, total_tokens=120),
        )
    )

    reviewer = ReviewerAgent(llm_provider=mock_provider)
    result = await reviewer.review(
        issue_title="Bug",
        issue_body="Desc",
        plan=sample_plan,
        patch=sample_patch,
        test_result=sample_test_result,
        source_files={"math.py": "a + b\n"},
    )

    # ReviewerAgent must override recommendation to "request_changes"
    assert result.recommendation == "request_changes"
