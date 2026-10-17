"""Unit and regression tests for strongly typed RepositoryContext, cryptographic provenance, and node integrity guards."""
import pytest
from app.core.security import compute_sha256
from app.orchestration.nodes import coder_node, planner_node
from app.orchestration.state import DevSquadState, create_initial_state
from app.schemas.repository_context import (
    ContextFile,
    ContextRetrievalLimitations,
    OmittedContextFile,
    RepositoryContext,
    TruncationMetadata,
)
from app.services.context_ranker import ContextRanker, RankedFile, RankedContextPackage


VALID_PROD_SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
ANOTHER_PROD_SHA = "9876543210fedcba0987654321fedcba01234567"


def test_valid_repository_context_production():
    """Verify production repository context with valid 40-char SHA and verified files."""
    code = "def add(a, b):\n    return a + b\n"
    code_hash = compute_sha256(code)

    file_item = ContextFile(
        path="src/math_ops.py",
        content=code,
        sha256=code_hash,
        commit_sha=VALID_PROD_SHA,
        size_bytes=len(code.encode("utf-8")),
        estimated_tokens=len(code) // 4,
        relevance_score=100.0,
        selection_explanation="Direct math operations module",
    )

    truncation = TruncationMetadata(
        is_truncated=False,
        total_files_in_tree=1,
        total_bytes_in_tree=len(code.encode("utf-8")),
        selected_files_count=1,
        omitted_files_count=0,
        budget_bytes=50000,
        consumed_bytes=len(code.encode("utf-8")),
        estimated_total_tokens=len(code) // 4,
        truncation_reasons=[],
    )

    limitations = ContextRetrievalLimitations(
        max_budget_bytes=50000,
        excluded_patterns=[".env", "node_modules"],
        retrieval_strategy="github_live_tree",
        is_partial_representation=False,
        warnings=[],
    )

    ctx = RepositoryContext(
        repo_owner="acme-corp",
        repo_name="calculator",
        target_branch="main",
        base_commit_sha=VALID_PROD_SHA,
        is_fixture=False,
        selected_files=[file_item],
        omitted_files=[],
        truncation=truncation,
        limitations=limitations,
        summary="Selected 1 file for calculator.",
    )

    assert ctx.repo_full_name == "acme-corp/calculator"
    assert ctx.verify_integrity() is True
    assert ctx.selected_files[0].sha256 == code_hash
    assert ctx.selected_files[0].content_hash == code_hash


def test_valid_repository_context_fixture():
    """Verify test fixture context with explicit fixture identifier."""
    code = "print('fixture content')\n"
    code_hash = compute_sha256(code)
    fixture_sha = "fixture-base-sha-00000000"

    file_item = ContextFile(
        path="tests/mock_file.py",
        content=code,
        sha256=code_hash,
        commit_sha=fixture_sha,
        size_bytes=len(code.encode("utf-8")),
        estimated_tokens=len(code) // 4,
    )

    truncation = TruncationMetadata(
        is_truncated=False,
        total_files_in_tree=1,
        total_bytes_in_tree=len(code.encode("utf-8")),
        selected_files_count=1,
        omitted_files_count=0,
        budget_bytes=10000,
        consumed_bytes=len(code.encode("utf-8")),
        estimated_total_tokens=len(code) // 4,
    )

    limitations = ContextRetrievalLimitations(
        max_budget_bytes=10000,
        retrieval_strategy="test_fixture",
        is_partial_representation=False,
    )

    ctx = RepositoryContext(
        repo_owner="local",
        repo_name="fixture-repo",
        target_branch="main",
        base_commit_sha=fixture_sha,
        is_fixture=True,
        fixture_identifier="offline-unit-fixture-v1",
        selected_files=[file_item],
        truncation=truncation,
        limitations=limitations,
        summary="Fixture repository context.",
    )

    assert ctx.is_fixture is True
    assert ctx.fixture_identifier == "offline-unit-fixture-v1"
    assert ctx.verify_integrity() is True


def test_fixture_context_cannot_be_marked_as_production():
    """Synthetic commit SHA must be rejected if is_fixture is False."""
    truncation = TruncationMetadata(
        is_truncated=False,
        total_files_in_tree=0,
        total_bytes_in_tree=0,
        selected_files_count=0,
        omitted_files_count=0,
        budget_bytes=10000,
        consumed_bytes=0,
        estimated_total_tokens=0,
    )
    limitations = ContextRetrievalLimitations(
        max_budget_bytes=10000,
        retrieval_strategy="test_fixture",
        is_partial_representation=False,
    )

    # 1. Non-hex string in production context
    with pytest.raises(ValueError, match="Production context requires a valid 7-40 hex character commit SHA"):
        RepositoryContext(
            repo_owner="owner",
            repo_name="repo",
            target_branch="main",
            base_commit_sha="invalid-commit-sha-xyz",
            is_fixture=False,
            truncation=truncation,
            limitations=limitations,
            summary="test",
        )

    # 2. Synthetic name with fixture prefix in production
    with pytest.raises(ValueError, match="Synthetic commit SHA"):
        RepositoryContext(
            repo_owner="owner",
            repo_name="repo",
            target_branch="main",
            base_commit_sha="fixture-sha-1234567890abcdef",
            is_fixture=False,
            truncation=truncation,
            limitations=limitations,
            summary="test",
        )


def test_fixture_context_requires_fixture_identifier():
    """If is_fixture is True, an explicit fixture_identifier must be provided."""
    truncation = TruncationMetadata(
        is_truncated=False,
        total_files_in_tree=0,
        total_bytes_in_tree=0,
        selected_files_count=0,
        omitted_files_count=0,
        budget_bytes=10000,
        consumed_bytes=0,
        estimated_total_tokens=0,
    )
    limitations = ContextRetrievalLimitations(
        max_budget_bytes=10000,
        retrieval_strategy="test_fixture",
        is_partial_representation=False,
    )

    with pytest.raises(ValueError, match="Fixture context must have an explicit, non-empty 'fixture_identifier'"):
        RepositoryContext(
            repo_owner="owner",
            repo_name="repo",
            target_branch="main",
            base_commit_sha="fixture-sha-0000",
            is_fixture=True,
            fixture_identifier=None,
            truncation=truncation,
            limitations=limitations,
            summary="test",
        )


def test_content_hash_mismatch_rejected():
    """ContextFile rejects hash declarations that do not match computed content SHA-256."""
    code = "secret_code = True"
    bad_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    with pytest.raises(ValueError, match="Content hash mismatch"):
        ContextFile(
            path="src/secret.py",
            content=code,
            sha256=bad_hash,
            commit_sha=VALID_PROD_SHA,
            size_bytes=len(code),
            estimated_tokens=5,
        )


def test_tampered_content_fails_verify_integrity():
    """Altering content post-creation causes verify_integrity to fail."""
    code = "original = 1"
    code_hash = compute_sha256(code)

    file_item = ContextFile(
        path="src/config.py",
        content=code,
        sha256=code_hash,
        commit_sha=VALID_PROD_SHA,
        size_bytes=len(code),
        estimated_tokens=3,
    )

    ctx = RepositoryContext(
        repo_owner="owner",
        repo_name="repo",
        target_branch="main",
        base_commit_sha=VALID_PROD_SHA,
        is_fixture=False,
        selected_files=[file_item],
        truncation=TruncationMetadata(
            is_truncated=False,
            total_files_in_tree=1,
            total_bytes_in_tree=len(code),
            selected_files_count=1,
            omitted_files_count=0,
            budget_bytes=1000,
            consumed_bytes=len(code),
            estimated_total_tokens=3,
        ),
        limitations=ContextRetrievalLimitations(
            max_budget_bytes=1000,
            retrieval_strategy="github_live_tree",
            is_partial_representation=False,
        ),
        summary="Test context",
    )
    assert ctx.verify_integrity() is True

    # Tamper with file content
    object.__setattr__(ctx.selected_files[0], "content", "tampered = 999")
    with pytest.raises(ValueError, match="Integrity check failed: content hash mismatch"):
        ctx.verify_integrity()


def test_mixed_commit_revisions_strictly_rejected():
    """Selecting files from different commits within one RepositoryContext is prohibited."""
    code1 = "v1 = 1"
    code2 = "v2 = 2"

    file1 = ContextFile(
        path="src/file1.py",
        content=code1,
        sha256=compute_sha256(code1),
        commit_sha=VALID_PROD_SHA,
        size_bytes=len(code1),
        estimated_tokens=2,
    )
    file2 = ContextFile(
        path="src/file2.py",
        content=code2,
        sha256=compute_sha256(code2),
        commit_sha=ANOTHER_PROD_SHA,  # Different commit revision!
        size_bytes=len(code2),
        estimated_tokens=2,
    )

    with pytest.raises(ValueError, match="Commit revision mismatch in file 'src/file2.py'"):
        RepositoryContext(
            repo_owner="owner",
            repo_name="repo",
            target_branch="main",
            base_commit_sha=VALID_PROD_SHA,
            is_fixture=False,
            selected_files=[file1, file2],
            truncation=TruncationMetadata(
                is_truncated=False,
                total_files_in_tree=2,
                total_bytes_in_tree=len(code1) + len(code2),
                selected_files_count=2,
                omitted_files_count=0,
                budget_bytes=1000,
                consumed_bytes=len(code1) + len(code2),
                estimated_total_tokens=4,
            ),
            limitations=ContextRetrievalLimitations(
                max_budget_bytes=1000,
                retrieval_strategy="github_live_tree",
                is_partial_representation=False,
            ),
            summary="Test",
        )


def test_unsafe_paths_and_traversal_rejected():
    """Ensure path traversal, absolute paths, null bytes, and windows drive letters are rejected."""
    code = "pass"
    code_hash = compute_sha256(code)

    unsafe_paths = [
        "../outside.py",
        "dir/../../etc/passwd",
        "/absolute/path/file.py",
        "\\windows\\path.py",
        "C:/drive/file.py",
        "src/\0nullbyte.py",
        "",
        "   ",
        "./relative_dot.py",
    ]

    for bad_path in unsafe_paths:
        with pytest.raises(ValueError):
            ContextFile(
                path=bad_path,
                content=code,
                sha256=code_hash,
                commit_sha=VALID_PROD_SHA,
                size_bytes=len(code),
                estimated_tokens=1,
            )


def test_truncated_context_records_explicit_warnings():
    """Verify ContextRanker records truncation, omitted reasons, and partial warnings."""
    ranker = ContextRanker(context_budget_bytes=150)
    files = [
        {"path": "src/primary.py", "content": "a = 1\n" * 10},   # ~60 bytes
        {"path": "src/secondary.py", "content": "b = 2\n" * 15}, # ~90 bytes
        {"path": "src/tertiary.py", "content": "c = 3\n" * 20},  # ~120 bytes (exceeds budget)
    ]

    repo_ctx = ranker.build_repository_context(
        files_data=files,
        issue_title="Bug in primary",
        issue_body="Fix src/primary.py",
        repo_owner="corp",
        repo_name="app",
        target_branch="main",
        base_commit_sha=VALID_PROD_SHA,
        is_fixture=False,
        total_tree_files=10,
        total_tree_bytes=1000,
    )

    assert repo_ctx.truncation.is_truncated is True
    assert repo_ctx.truncation.omitted_files_count > 0
    assert repo_ctx.limitations.is_partial_representation is True
    assert any("partial" in w.lower() for w in repo_ctx.limitations.warnings)
    assert any("budget" in w.lower() for w in repo_ctx.limitations.warnings)
    assert repo_ctx.verify_integrity() is True


def test_backward_compatibility_ranker_and_state():
    """Verify rank_and_package and create_initial_state remain backwards-compatible."""
    ranker = ContextRanker()
    files = [{"path": "src/app.py", "content": "print('hello')"}]
    pkg = ranker.rank_and_package(files, "Issue title")

    assert isinstance(pkg, RankedContextPackage)
    assert len(pkg.selected_files) == 1
    assert pkg.selected_files[0].path == "src/app.py"
    assert pkg.selected_files[0].content_hash == compute_sha256("print('hello')")
    assert pkg.selected_files[0].sha256 == pkg.selected_files[0].content_hash

    # Verify state initialization
    state = create_initial_state(
        run_id="run-rc-test",
        repository_id="repo-1",
        issue_id="issue-1",
    )
    assert "repository_context" in state
    assert state["repository_context"] is None


@pytest.mark.asyncio
async def test_node_guards_catch_compromised_context():
    """Planner and Coder nodes fail fast with CONTEXT_INTEGRITY_COMPROMISED when context is tampered."""
    code = "valid = True"
    code_hash = compute_sha256(code)

    file_item = ContextFile(
        path="src/valid.py",
        content=code,
        sha256=code_hash,
        commit_sha=VALID_PROD_SHA,
        size_bytes=len(code),
        estimated_tokens=2,
    )

    ctx = RepositoryContext(
        repo_owner="owner",
        repo_name="repo",
        target_branch="main",
        base_commit_sha=VALID_PROD_SHA,
        is_fixture=False,
        selected_files=[file_item],
        truncation=TruncationMetadata(
            is_truncated=False,
            total_files_in_tree=1,
            total_bytes_in_tree=len(code),
            selected_files_count=1,
            omitted_files_count=0,
            budget_bytes=1000,
            consumed_bytes=len(code),
            estimated_total_tokens=2,
        ),
        limitations=ContextRetrievalLimitations(
            max_budget_bytes=1000,
            retrieval_strategy="github_live_tree",
            is_partial_representation=False,
        ),
        summary="Test",
    )

    # Tamper with file content in dictionary representation
    compromised_dict = ctx.model_dump()
    compromised_dict["selected_files"][0]["content"] = "malicious_injection = True"

    state: DevSquadState = {
        "run_id": "test-run-tamper",
        "repository_context": compromised_dict,
        "metadata": {
            "ranked_context": {
                "selected_files": [{"path": "src/valid.py", "content": "valid = True", "content_hash": code_hash, "relevance_score": 1.0, "selection_explanation": "e", "size_bytes": 10, "estimated_tokens": 2}],
                "omitted_files": [],
                "total_bytes": 10,
                "total_estimated_tokens": 2,
                "budget_bytes": 1000,
                "truncated": False,
                "context_summary": "summary",
            },
        },
    }

    # 1. Test Planner guard
    planner_result = await planner_node(state)
    assert planner_result["status"] == "FAILED"
    assert planner_result["error_code"] == "CONTEXT_INTEGRITY_COMPROMISED"

    # 2. Test Coder guard
    state["plan"] = {
        "objective": "Fix",
        "steps": [{"id": "s1", "description": "d", "target_files": ["src/valid.py"], "dependencies": []}],
        "acceptance_criteria": ["ac1"],
        "regression_risks": [],
        "uncertainties": [],
        "assumptions": [],
    }
    coder_result = await coder_node(state)
    assert coder_result["status"] == "FAILED"
    assert coder_result["error_code"] == "CONTEXT_INTEGRITY_COMPROMISED"
