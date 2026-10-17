"""Integration tests verifying database transaction rollback behavior."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User


@pytest.mark.asyncio
async def test_transaction_rollback_on_error(test_db_session: AsyncSession):
    # Add a user successfully
    user1 = User(email="committed@example.com", display_name="Committed User")
    test_db_session.add(user1)
    await test_db_session.commit()

    # Begin uncommitted transaction with a failing insert
    user2 = User(email="rollback@example.com", display_name="Rollback User")
    test_db_session.add(user2)

    # Intentionally trigger rollback
    await test_db_session.rollback()

    # Verify user2 does not exist in database
    result = await test_db_session.execute(
        select(User).where(User.email == "rollback@example.com")
    )
    assert result.scalar_one_or_none() is None

    # Verify user1 is still present
    result_committed = await test_db_session.execute(
        select(User).where(User.email == "committed@example.com")
    )
    assert result_committed.scalar_one_or_none() is not None
