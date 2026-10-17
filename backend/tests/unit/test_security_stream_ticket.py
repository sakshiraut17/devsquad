"""Unit tests for single-purpose short-lived stream tickets, replay protection, and startup recovery."""
import time
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_stream_ticket, verify_stream_ticket
from app.db.models.issue import Issue
from app.db.models.repository import Repository
from app.db.models.run import Run, RunStatus
from app.db.models.user import User


@pytest.fixture
async def sample_run_fixture(test_db_session: AsyncSession, default_user: User):
    """Fixture providing an authorized repository, issue, and run."""
    repo = Repository(
        owner_id=default_user.id,
        github_repository_id=9902,
        full_name="devsquad-org/ticket-repo",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        repository_id=repo.id,
        github_issue_number=1,
        title="Streaming ticket issue",
        body="Verify single-purpose stream tickets.",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.QUEUED.value,
        current_node="idle",
    )
    test_db_session.add(run)
    await test_db_session.commit()
    await test_db_session.refresh(run)
    return repo, issue, run



def test_create_and_verify_stream_ticket_success():
    """Verify that a valid stream ticket is generated and verified with matching run_id."""
    user_id = "user-123"
    run_id = "run-456"

    ticket = create_stream_ticket(user_id=user_id, run_id=run_id, expires_in_seconds=60)
    assert isinstance(ticket, str)
    assert len(ticket.split(".")) == 3

    payload = verify_stream_ticket(ticket=ticket, expected_run_id=run_id, consume=False)
    assert payload["sub"] == user_id
    assert payload["run_id"] == run_id
    assert payload["purpose"] == "run_stream"
    assert "jti" in payload
    assert payload["exp"] > int(time.time())


def test_stream_ticket_run_mismatch_rejection():
    """Verify that a stream ticket minted for run-A cannot be used for run-B."""
    ticket = create_stream_ticket(user_id="user-1", run_id="run-A", expires_in_seconds=60)

    with pytest.raises(ValueError, match="Stream ticket run mismatch"):
        verify_stream_ticket(ticket=ticket, expected_run_id="run-B", consume=False)


def test_stream_ticket_tampering_rejection():
    """Verify that signature verification fails if ticket payload or signature is modified."""
    ticket = create_stream_ticket(user_id="user-1", run_id="run-A", expires_in_seconds=60)
    parts = ticket.split(".")
    tampered_payload = parts[1] + "tamper"
    tampered_ticket = f"{parts[0]}.{tampered_payload}.{parts[2]}"

    with pytest.raises(ValueError):
        verify_stream_ticket(ticket=tampered_ticket, expected_run_id="run-A", consume=False)


def test_stream_ticket_expiration_rejection():
    """Verify that expired stream tickets are rejected fail-closed."""
    ticket = create_stream_ticket(user_id="user-1", run_id="run-A", expires_in_seconds=-10)

    with pytest.raises(ValueError, match="Stream ticket has expired"):
        verify_stream_ticket(ticket=ticket, expected_run_id="run-A", consume=False)


def test_stream_ticket_replay_protection():
    """Verify that a consumed stream ticket cannot be replayed."""
    ticket = create_stream_ticket(user_id="user-1", run_id="run-replay", expires_in_seconds=60)

    # First consumption succeeds
    payload1 = verify_stream_ticket(ticket=ticket, expected_run_id="run-replay", consume=True)
    assert payload1["sub"] == "user-1"

    # Second consumption must raise replay detected error
    with pytest.raises(ValueError, match="replay detected"):
        verify_stream_ticket(ticket=ticket, expected_run_id="run-replay", consume=True)


@pytest.mark.asyncio
async def test_stream_ticket_endpoint_requires_auth(unauthenticated_client: AsyncClient, sample_run_fixture):
    """Verify POST /runs/{id}/stream-ticket rejects unauthenticated requests."""
    repo, issue, run = sample_run_fixture
    resp = await unauthenticated_client.post(f"/api/v1/runs/{run.id}/stream-ticket")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_stream_ticket_endpoint_mismatched_owner_forbidden(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    sample_run_fixture,
):
    """Verify that a user who does not own the repository cannot generate a stream ticket."""
    repo, issue, run = sample_run_fixture
    other_user = User(
        id="00000000-0000-0000-0000-000000000099",
        email="other@devsquad.ai",
        display_name="Other User",
        is_active=True,
    )
    test_db_session.add(other_user)
    await test_db_session.commit()

    # Assign repo to other_user
    repo.owner_id = other_user.id
    await test_db_session.commit()

    attacker_token = create_access_token(user_id="00000000-0000-0000-0000-000000000088", email="attacker@example.com")
    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/stream-ticket",
        headers={"Authorization": f"Bearer {attacker_token}"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_lifespan_startup_orphan_reconciliation(test_db_session: AsyncSession, sample_run_fixture):
    """Verify that application lifespan startup automatically reconciles orphaned in-progress runs."""
    repo, issue, run = sample_run_fixture
    run.status = RunStatus.CODING.value
    await test_db_session.commit()

    from app.main import lifespan
    from app.main import app

    async with lifespan(app):
        # After lifespan startup context entered, the run should be reconciled
        await test_db_session.refresh(run)
        assert run.status == RunStatus.FAILED.value
        assert "interrupted by system restart" in (run.error_summary or "").lower()

