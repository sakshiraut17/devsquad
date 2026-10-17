"""Unit tests for CoderAgent."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.exceptions import ValidationError
from app.core.security import compute_sha256
from app.schemas.plan import PlanStep, StructuredPlan
from app.services.agents.coder import CoderAgent, PatchGenerationResponse
from app.services.agents.diff_utils import PatchError
from app.services.llm.base import LLMResponse, LLMUsage


@pytest.fixture
def sample_plan():
    return StructuredPlan(
        objective="Fix math subtraction error",
        problem_summary="subtract function returns addition",
        steps=[
            PlanStep(
                id="step-1",
                description="Fix subtraction operator",
                target_files=["math_lib.py"],
                dependencies=[],
                rationale="Logic error",
            )
        ],
        acceptance_criteria=["subtract(5, 3) == 2"],
        required_tests=["tests/test_math.py"],
        risks=[],
        assumptions=[],
        uncertainties=[],
    )


@pytest.mark.asyncio
async def test_coder_agent_generates_valid_patch(sample_plan):
    source_files = {"math_lib.py": "def subtract(a, b):\n    return a + b\n"}
    valid_diff = """--- a/math_lib.py
+++ b/math_lib.py
@@ -1,2 +1,2 @@
 def subtract(a, b):\n-    return a + b
+    return a - b
"""
    expected_resp = PatchGenerationResponse(
        summary="Fix subtraction operator",
        target_files=["math_lib.py"],
        unified_diff=valid_diff,
        rationale="Replaced + with -",
    )

    mock_provider = MagicMock()
    mock_provider.generate_structured = AsyncMock(
        return_value=LLMResponse(
            data=expected_resp,
            raw_response="{}",
            provider="gemini",
            model="gemini-2.0-flash",
            usage=LLMUsage(latency_ms=120.0, prompt_tokens=80, completion_tokens=40, total_tokens=120),
        )
    )

    coder = CoderAgent(llm_provider=mock_provider)
    patch_item = await coder.generate_patch(
        plan=sample_plan,
        source_files=source_files,
        base_commit_sha="abcdef123456",
        revision=1,
    )

    assert patch_item.revision == 1
    assert patch_item.target_files == ["math_lib.py"]
    assert patch_item.base_commit_sha == "abcdef123456"
    assert "math_lib.py" in patch_item.file_hashes
    # Content hash must equal sha256 of unified diff computed by application
    assert patch_item.content_hash == compute_sha256(valid_diff.strip())


@pytest.mark.asyncio
async def test_coder_agent_rejects_path_traversal(sample_plan):
    source_files = {"math_lib.py": "def subtract(a, b):\n    return a + b\n"}
    traversal_diff = """--- a/../../etc/passwd
+++ b/../../etc/passwd
@@ -1,1 +1,1 @@
-root
+attacker
"""
    bad_resp = PatchGenerationResponse(
        summary="Malicious path",
        target_files=["../../etc/passwd"],
        unified_diff=traversal_diff,
        rationale="Attack",
    )

    mock_provider = MagicMock()
    mock_provider.generate_structured = AsyncMock(
        return_value=LLMResponse(
            data=bad_resp,
            raw_response="{}",
            provider="gemini",
            model="gemini-2.0-flash",
            usage=LLMUsage(latency_ms=100.0, prompt_tokens=50, completion_tokens=25, total_tokens=75),
        )
    )

    coder = CoderAgent(llm_provider=mock_provider)
    with pytest.raises(PatchError) as exc:
        await coder.generate_patch(
            plan=sample_plan,
            source_files=source_files,
            base_commit_sha="abc12345",
        )
    assert "Unsafe path detected" in str(exc.value)


@pytest.mark.asyncio
async def test_coder_agent_rejects_hunk_mismatch(sample_plan):
    # Source file does not match the context lines in diff
    source_files = {"math_lib.py": "def different_function():\n    pass\n"}
    mismatch_diff = """--- a/math_lib.py
+++ b/math_lib.py
@@ -1,2 +1,2 @@
 def subtract(a, b):\n-    return a + b
+    return a - b
"""
    mismatch_resp = PatchGenerationResponse(
        summary="Mismatch diff",
        target_files=["math_lib.py"],
        unified_diff=mismatch_diff,
        rationale="Test mismatch",
    )

    mock_provider = MagicMock()
    mock_provider.generate_structured = AsyncMock(
        return_value=LLMResponse(
            data=mismatch_resp,
            raw_response="{}",
            provider="gemini",
            model="gemini-2.0-flash",
            usage=LLMUsage(latency_ms=100.0, prompt_tokens=50, completion_tokens=25, total_tokens=75),
        )
    )

    coder = CoderAgent(llm_provider=mock_provider)
    with pytest.raises(PatchError) as exc:
        await coder.generate_patch(
            plan=sample_plan,
            source_files=source_files,
            base_commit_sha="abc12345",
        )
    assert "Failed to apply patch" in str(exc.value)


@pytest.mark.asyncio
async def test_coder_agent_includes_repair_feedback(sample_plan):
    source_files = {"math_lib.py": "def subtract(a, b):\n    return a + b\n"}
    valid_diff = """--- a/math_lib.py
+++ b/math_lib.py
@@ -1,2 +1,2 @@
 def subtract(a, b):\n-    return a + b
+    return a - b
"""
    expected_resp = PatchGenerationResponse(
        summary="Fix subtraction",
        target_files=["math_lib.py"],
        unified_diff=valid_diff,
        rationale="Repair cycle revision 2",
    )

    mock_provider = MagicMock()
    mock_provider.generate_structured = AsyncMock(
        return_value=LLMResponse(
            data=expected_resp,
            raw_response="{}",
            provider="gemini",
            model="gemini-2.0-flash",
            usage=LLMUsage(latency_ms=100.0, prompt_tokens=50, completion_tokens=25, total_tokens=75),
        )
    )

    coder = CoderAgent(llm_provider=mock_provider)
    _ = await coder.generate_patch(
        plan=sample_plan,
        source_files=source_files,
        base_commit_sha="abc12345",
        revision=2,
        previous_feedback="Test failed with AssertionError on subtract(5, 3)",
    )

    call_args = mock_provider.generate_structured.call_args
    user_prompt = call_args[1]["user_prompt"]
    assert "PREVIOUS VALIDATION / REVIEW FEEDBACK" in user_prompt
    assert "AssertionError on subtract(5, 3)" in user_prompt
