"""Integration tests for orchestration cancellation, concurrency safety, and task cleanup."""
import asyncio
import tempfile
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Issue,
    Repository,
    Run,
    RunStatus,
    User,
)
from app.orchestration import (
    DevSquadOrchestrator,
    NodeDependencies,
    OrchestrationError,
    RunNotResumableError,
    WorkflowStatus,
    set_default_deps,
)
from app.orchestration.service import _active_tasks, _registry_lock


@pytest.mark.asyncio
async def test_concurrent_run_execution_prevention(test_db_session: AsyncSession):
    """Ensure that concurrent start or resume attempts on an already active run are strictly rejected."""
    user = User(email="concurrency@devsquad.ai", display_name="Concurrency Tester")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(
        owner_id=user.id,
        github_repository_id=7771,
        full_name="devsquad/concurrency-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Concurrent run test",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-concurrent-001",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.CODING.value,
        current_node="coder",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        chk_db = tmp.name

    orchestrator = DevSquadOrchestrator(checkpoint_db_path=chk_db)

    # Simulate an active background task currently executing
    fake_running_task = asyncio.create_task(asyncio.sleep(10))
    async with _registry_lock:
        _active_tasks[run.id] = fake_running_task

    try:
        # Starting an active run must fail
        with pytest.raises(OrchestrationError, match="already actively executing"):
            await orchestrator.start_run(run.id, db=test_db_session)

        # Resuming an active run must fail
        with pytest.raises(OrchestrationError, match="already actively executing"):
            await orchestrator.resume_run(run.id, db=test_db_session)
    finally:
        fake_running_task.cancel()
        try:
            await fake_running_task
        except asyncio.CancelledError:
            pass
        async with _registry_lock:
            _active_tasks.pop(run.id, None)


@pytest.mark.asyncio
async def test_idempotent_cancel_run(test_db_session: AsyncSession):
    """Ensure cancel_run is completely idempotent and handles terminal runs accurately."""
    user = User(email="canceller@devsquad.ai", display_name="Canceller")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(
        owner_id=user.id,
        github_repository_id=7772,
        full_name="devsquad/cancel-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=2,
        title="Cancel idempotency test",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-cancel-002",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.TESTING.value,
        current_node="tester",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        chk_db = tmp.name

    orchestrator = DevSquadOrchestrator(checkpoint_db_path=chk_db)

    # 1. First cancellation call -> Successfully cancels
    cancelled_state_1 = await orchestrator.cancel_run(run.id, db=test_db_session, reason="User cancelled test")
    assert cancelled_state_1["status"] == WorkflowStatus.CANCELLED.value

    await test_db_session.refresh(run)
    assert run.status == RunStatus.CANCELLED.value
    assert run.finished_at is not None

    # 2. Second cancellation call -> Idempotent success without error
    cancelled_state_2 = await orchestrator.cancel_run(run.id, db=test_db_session, reason="Duplicate request")
    assert cancelled_state_2["status"] == WorkflowStatus.CANCELLED.value
    assert cancelled_state_2["run_id"] == run.id

    # 3. Completed run cannot be cancelled
    run.status = RunStatus.COMPLETED.value
    await test_db_session.commit()

    with pytest.raises(OrchestrationError, match="already COMPLETED"):
        await orchestrator.cancel_run(run.id, db=test_db_session)


@pytest.mark.asyncio
async def test_cooperative_cancellation_during_execution(
    test_db_session: AsyncSession,
    mock_agents,
):
    """Verify that an in-flight workflow can be cancelled cooperatively during agent execution."""
    planner, coder, tester, reviewer = mock_agents

    # Configure planner agent to sleep simulating work
    async def slow_plan(*args, **kwargs):
        await asyncio.sleep(0.5)
        return planner.plan.return_value

    planner.plan = AsyncMock(side_effect=slow_plan)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(
        bind=test_db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    deps = NodeDependencies(
        session_factory=session_factory,
        planner_agent=planner,
        coder_agent=coder,
        tester_agent=tester,
        reviewer_agent=reviewer,
    )
    set_default_deps(deps)

    user = User(email="cooperative@devsquad.ai", display_name="Coop User")
    test_db_session.add(user)
    await test_db_session.commit()

    repo = Repository(
        owner_id=user.id,
        github_repository_id=7773,
        full_name="devsquad/coop-cancel",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=3,
        title="Cooperative cancellation",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-cancel-coop",
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

    async with session_factory() as run_session:
        # Launch workflow in background task with dedicated session
        run_task = asyncio.create_task(
            orchestrator.start_run(
                run_id=run.id,
                db=run_session,
                metadata={"source_files": {"app.py": "x=1\n"}, "is_test_fixture": True},
            )
        )

        # Allow workflow to start and enter planner
        await asyncio.sleep(0.1)

        # Cancel while active using separate cancel session
        async with session_factory() as cancel_session:
            await orchestrator.cancel_run(run.id, db=cancel_session, reason="User triggered stop")

        # Await workflow task
        result_state = await run_task

    assert result_state["status"] == WorkflowStatus.CANCELLED.value
    await test_db_session.refresh(run)
    assert run.status == RunStatus.CANCELLED.value

    # Verify registry cleanup
    async with _registry_lock:
        assert run.id not in _active_tasks
