"""Unit tests for bounded repair cycle and persistence helpers."""

import pytest
from app.db.models.agent_log import AgentLog
from app.db.models.patch import Patch
from app.db.models.run import Run
from app.schemas.patch import PatchItem
from app.schemas.review import ReviewFinding, ReviewResponse
from app.schemas.test_result import TestResult
from app.services.agents.repair import (
    RepairCycleState,
    log_agent_event,
    record_patch_revision,
)


@pytest.fixture
def sample_patch():
    return PatchItem(
        unified_diff="--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new\n",
        target_files=["file.py"],
        base_commit_sha="commit_sha_123",
        file_hashes={"file.py": "hash1"},
        summary="Sample patch",
        revision=1,
        content_hash="contenthash123",
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
    )


def test_repair_cycle_state_transitions(sample_patch, sample_test_result):
    state = RepairCycleState(run_id="run-123", max_revisions=2)
    assert state.current_revision == 1
    assert not state.is_terminal

    # Add revision 1
    state.add_revision(sample_patch, sample_test_result)
    assert len(state.history) == 1
    assert state.current_revision == 2
    assert not state.is_terminal

    # Add revision 2
    patch2 = sample_patch.model_copy(update={"revision": 2, "content_hash": "hash2"})
    state.add_revision(patch2, sample_test_result)
    assert len(state.history) == 2
    assert state.current_revision == 3
    # Exceeded max_revisions (2), so is_terminal must be True
    assert state.is_terminal is True
    assert state.terminal_status == "MAX_RETRIES_EXCEEDED"


def test_repair_cycle_get_latest_feedback(sample_patch, sample_test_result):
    state = RepairCycleState(run_id="run-123")
    assert state.get_latest_feedback() is None

    review = ReviewResponse(
        findings=[
            ReviewFinding(
                id="FIND-1",
                severity="HIGH",
                category="correctness",
                file_path="file.py",
                line_number=5,
                description="Null pointer exception on empty input",
                evidence="if not input: ...",
                recommendation="Add guard clause",
            )
        ],
        acceptance_criteria_met=False,
        recommendation="request_changes",
        unresolved_risks=[],
    )

    state.add_revision(sample_patch, sample_test_result, review)
    feedback = state.get_latest_feedback()
    assert feedback is not None
    assert "Null pointer exception" in feedback
    assert "Add guard clause" in feedback


from app.db.models.issue import Issue
from app.db.models.repository import Repository
from app.db.models.user import User


@pytest.mark.asyncio
async def test_record_patch_revision_and_log_agent_event_persistence(test_db_session, sample_patch):
    user = User(email="coder@example.com", display_name="Coder")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(
        owner_id=user.id,
        github_repository_id=9999,
        full_name="devsquad/repair-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=10,
        title="Repair issue",
        body="Details",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    # Create a parent run entity
    run = Run(
        id="test-run-456",
        repository_id=repo.id,
        issue_id=issue.id,
        status="CODING",
        current_node="coder",
    )
    test_db_session.add(run)
    await test_db_session.commit()


    # 1. Test record_patch_revision
    patch_entity = await record_patch_revision(
        session=test_db_session,
        run_id="test-run-456",
        patch_item=sample_patch,
        validation_status="VALIDATED",
    )
    assert patch_entity.id is not None
    assert patch_entity.run_id == "test-run-456"
    assert patch_entity.revision == 1
    assert patch_entity.content_hash == sample_patch.content_hash

    # 2. Test log_agent_event
    log_entity = await log_agent_event(
        session=test_db_session,
        run_id="test-run-456",
        agent_name="coder",
        event_type="patch_generated",
        message="Generated revision 1",
        input_summary="Plan with 1 step",
        output_summary=f"Modified files: {', '.join(sample_patch.target_files)}",
        duration_ms=120,
    )
    assert log_entity.id is not None
    assert log_entity.run_id == "test-run-456"
    assert log_entity.agent_name == "coder"
    assert "file.py" in log_entity.output_summary
    assert log_entity.duration_ms == 120


