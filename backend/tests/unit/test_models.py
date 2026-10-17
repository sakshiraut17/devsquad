"""Unit tests for SQLAlchemy models, relationships, and constraints."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    ApprovalRecord,
    Issue,
    Patch,
    PullRequest,
    Repository,
    Run,
    RunStatus,
    User,
)


@pytest.mark.asyncio
async def test_user_creation_and_uniqueness(test_db_session: AsyncSession):
    user = User(email="test@example.com", display_name="Test Dev")
    test_db_session.add(user)
    await test_db_session.commit()
    assert user.id is not None
    assert user.is_active is True

    # Duplicate email should fail
    duplicate = User(email="test@example.com", display_name="Test Dev 2")
    test_db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()


@pytest.mark.asyncio
async def test_repository_and_issue_relationship_and_uniqueness(test_db_session: AsyncSession):
    user = User(email="owner@example.com", display_name="Owner")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(
        owner_id=user.id,
        github_repository_id=1001,
        full_name="octocat/Hello-World",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    # Create issue #1
    issue1 = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Bug in auth",
        body="Details",
        state="open",
        labels=["bug"],
    )
    test_db_session.add(issue1)
    await test_db_session.commit()

    # Duplicate issue #1 in same repository must fail uniqueness constraint
    issue_dup = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Duplicate Bug",
    )
    test_db_session.add(issue_dup)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()


@pytest.mark.asyncio
async def test_run_patch_approval_audit_trail(test_db_session: AsyncSession):
    # Setup user, repo, issue
    user = User(email="maintainer@example.com", display_name="Maintainer")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(
        owner_id=user.id,
        github_repository_id=2002,
        full_name="org/project",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=42,
        title="Feature request",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    # Create Run
    run = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="await_human_approval",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    # Create Patch Revision 1
    patch1 = Patch(
        run_id=run.id,
        revision=1,
        unified_diff="--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-old\n+new",
        target_files=["main.py"],
        summary="Updated main logic",
        content_hash="abc123hash456",
        validation_status="validated",
    )
    test_db_session.add(patch1)
    await test_db_session.commit()

    run_id = run.id
    user_id = user.id
    patch1_id = patch1.id
    patch1_hash = patch1.content_hash

    # Duplicate revision for same run must fail
    patch_dup = Patch(
        run_id=run_id,
        revision=1,
        unified_diff="diff",
        target_files=["main.py"],
        summary="Another diff",
        content_hash="xyz789hash",
    )
    test_db_session.add(patch_dup)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # Create ApprovalRecord explicitly bound to patch hash
    approval = ApprovalRecord(
        run_id=run_id,
        patch_id=patch1_id,
        approver_id=user_id,
        decision="approved",
        patch_hash=patch1_hash,
        validation_evidence={"tests_passed": True, "exit_code": 0},
        feedback="Verified locally",
    )
    test_db_session.add(approval)
    await test_db_session.commit()

    assert approval.id is not None
    assert approval.patch_hash == "abc123hash456"
