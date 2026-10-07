import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User, Repository, Issue, Run, AgentLog, Patch, TestResult, PullRequest


@pytest.mark.asyncio
async def test_create_user_and_repository(db_session: AsyncSession):
    """Test creating a User and linking a Repository model."""
    user = User(
        github_id="123456",
        username="octocat",
        email="octocat@github.com",
        avatar_url="https://github.com/images/error/octocat_happy.gif",
    )
    db_session.add(user)
    await db_session.flush()

    repo = Repository(
        user_id=user.id,
        github_repo_id=987654321,
        full_name="octocat/Hello-World",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()

    # Query back
    result = await db_session.execute(select(Repository).where(Repository.full_name == "octocat/Hello-World"))
    fetched_repo = result.scalar_one_or_none()
    assert fetched_repo is not None
    assert fetched_repo.user_id == user.id
    assert fetched_repo.default_branch == "main"


@pytest.mark.asyncio
async def test_create_run_and_sub_entities(db_session: AsyncSession):
    """Test creating a workflow Run with AgentLogs, Patches, TestResults, and PullRequest."""
    user = User(github_id="999", username="testuser")
    db_session.add(user)
    await db_session.flush()

    repo = Repository(user_id=user.id, github_repo_id=111, full_name="testuser/demo")
    db_session.add(repo)
    await db_session.flush()

    issue = Issue(repository_id=repo.id, issue_number=1, title="Fix bug in auth module", body="Auth fails on empty string")
    db_session.add(issue)
    await db_session.flush()

    run = Run(repository_id=repo.id, issue_id=issue.id, status="planner_running")
    db_session.add(run)
    await db_session.flush()

    log = AgentLog(run_id=run.id, agent_name="planner", log_level="INFO", message="Started analyzing repository issue")
    patch = Patch(run_id=run.id, target_file="src/auth.py", unified_diff="--- a/src/auth.py\n+++ b/src/auth.py\n@@ -1,2 +1,2 @@\n-if not token:\n+if token is None or len(token) == 0:")
    test_res = TestResult(run_id=run.id, exit_code=0, stdout="1 passed in 0.05s", stderr="")
    pr = PullRequest(run_id=run.id, pr_number=42, pr_url="https://github.com/testuser/demo/pull/42", head_branch="devsquad/issue-1", base_branch="main")

    db_session.add_all([log, patch, test_res, pr])
    await db_session.commit()

    # Query back Run
    result = await db_session.execute(select(Run).where(Run.id == run.id))
    fetched_run = result.scalar_one_or_none()
    assert fetched_run is not None
    assert fetched_run.status == "planner_running"
