"""Unit tests for PlannerAgent."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.exceptions import ValidationError
from app.schemas.plan import PlanStep, StructuredPlan
from app.services.agents.planner import PlannerAgent
from app.services.context_ranker import RankedContextPackage, RankedFile
from app.services.llm.base import LLMResponse, LLMUsage


@pytest.fixture
def sample_ranked_context():
    return RankedContextPackage(
        selected_files=[
            RankedFile(
                path="app/auth.py",
                content="def login():\n    return False\n",
                content_hash="hash1",
                relevance_score=100.0,
                selection_explanation="Exact path match from issue",
                size_bytes=30,
                estimated_tokens=20,
            )
        ],
        omitted_files=[],
        total_estimated_tokens=20,
        total_bytes=30,
        budget_bytes=5242880,
        truncated=False,
        context_summary="Selected 1 file within budget.",
    )


@pytest.mark.asyncio
async def test_planner_agent_generates_valid_plan(sample_ranked_context):
    mock_provider = MagicMock()
    expected_plan = StructuredPlan(
        objective="Fix authentication return code",
        problem_summary="login() returns False instead of True",
        steps=[
            PlanStep(
                id="step-1",
                description="Change return value in login()",
                target_files=["app/auth.py"],
                dependencies=[],
                rationale="Required for user authentication",
            )
        ],
        acceptance_criteria=["login() returns True"],
        required_tests=["tests/test_auth.py"],
        risks=["Security regression if credentials not checked"],
        assumptions=[],
        uncertainties=[],
    )

    mock_resp = LLMResponse(
        data=expected_plan,
        raw_response="{}",
        provider="gemini",
        model="gemini-2.0-flash",
        usage=LLMUsage(latency_ms=150.0, prompt_tokens=100, completion_tokens=50, total_tokens=150),
    )
    mock_provider.generate_structured = AsyncMock(return_value=mock_resp)

    planner = PlannerAgent(llm_provider=mock_provider)
    result = await planner.plan(
        issue_title="Login fails",
        issue_body="Users cannot log in",
        issue_number=42,
        ranked_context=sample_ranked_context,
        repo_name="devsquad",
        repo_owner="org",
    )

    assert result.objective == expected_plan.objective
    assert len(result.steps) == 1
    assert result.steps[0].target_files == ["app/auth.py"]
    mock_provider.generate_structured.assert_called_once()


@pytest.mark.asyncio
async def test_planner_agent_rejects_unsafe_target_path(sample_ranked_context):
    mock_provider = MagicMock()
    unsafe_plan = StructuredPlan(
        objective="Malicious plan",
        problem_summary="Problem",
        steps=[
            PlanStep(
                id="step-1",
                description="Access parent directory",
                target_files=["../../etc/passwd"],
                dependencies=[],
                rationale="Unsafe path traversal",
            )
        ],
        acceptance_criteria=["Passwd modified"],
        required_tests=[],
        risks=[],
        assumptions=[],
        uncertainties=[],
    )

    mock_resp = LLMResponse(
        data=unsafe_plan,
        raw_response="{}",
        provider="gemini",
        model="gemini-2.0-flash",
        usage=LLMUsage(latency_ms=100.0, prompt_tokens=50, completion_tokens=25, total_tokens=75),
    )
    mock_provider.generate_structured = AsyncMock(return_value=mock_resp)

    planner = PlannerAgent(llm_provider=mock_provider)
    with pytest.raises(ValidationError) as exc:
        await planner.plan(
            issue_title="Bug",
            issue_body="Desc",
            issue_number=1,
            ranked_context=sample_ranked_context,
            repo_name="repo",
            repo_owner="owner",
        )
    assert "unsafe target file path" in str(exc.value)


@pytest.mark.asyncio
async def test_planner_flags_unranked_target_file_in_uncertainties(sample_ranked_context):
    mock_provider = MagicMock()
    plan_with_unranked_file = StructuredPlan(
        objective="Add feature in missing file",
        problem_summary="Target file not in context",
        steps=[
            PlanStep(
                id="step-1",
                description="Modify unranked file",
                target_files=["app/unranked_service.py"],
                dependencies=[],
                rationale="Needed for feature",
            )
        ],
        acceptance_criteria=["Done"],
        required_tests=[],
        risks=[],
        assumptions=[],
        uncertainties=[],
    )

    mock_resp = LLMResponse(
        data=plan_with_unranked_file,
        raw_response="{}",
        provider="gemini",
        model="gemini-2.0-flash",
        usage=LLMUsage(latency_ms=100.0, prompt_tokens=50, completion_tokens=25, total_tokens=75),
    )
    mock_provider.generate_structured = AsyncMock(return_value=mock_resp)

    planner = PlannerAgent(llm_provider=mock_provider)
    res = await planner.plan(
        issue_title="Bug",
        issue_body="Desc",
        issue_number=1,
        ranked_context=sample_ranked_context,
        repo_name="repo",
        repo_owner="owner",
    )
    # Target file 'app/unranked_service.py' was not in ranked_context, so it must be recorded in uncertainties
    assert any("app/unranked_service.py" in u for u in res.uncertainties)
