"""Integration test verifying Alembic migrations against a fresh temporary database."""
import os
import tempfile
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_migration_upgrade_from_empty_database():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        db_url = f"sqlite+aiosqlite:///{temp_db_path}"
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", db_url)

        # Run Alembic migration to head
        command.upgrade(cfg, "head")

        # Verify tables created
        engine = create_async_engine(db_url)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = set(r[0] for r in res.fetchall())

            # Expected tables
            expected = {
                "alembic_version",
                "users",
                "repositories",
                "issues",
                "runs",
                "agent_logs",
                "patches",
                "approval_records",
                "pull_requests",
            }
            assert expected.issubset(tables)

            # Verify alembic_version has the initial revision
            ver_res = await conn.execute(text("SELECT version_num FROM alembic_version;"))
            version_num = ver_res.scalar()
            assert version_num == "1a0c41410573"

        await engine.dispose()
    finally:
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except OSError:
                pass
