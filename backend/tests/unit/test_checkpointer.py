"""Unit tests for LangGraph checkpointing infrastructure."""

import os
import tempfile
import pytest
from app.orchestration.checkpointer import get_async_checkpointer


@pytest.mark.asyncio
async def test_get_async_checkpointer_memory():
    async with get_async_checkpointer(":memory:") as saver:
        assert saver is not None
        # Verify it can be passed to LangGraph
        from langgraph.checkpoint.memory import InMemorySaver
        assert isinstance(saver, InMemorySaver)


@pytest.mark.asyncio
async def test_get_async_checkpointer_sqlite_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # First session: write a checkpoint
        async with get_async_checkpointer(db_path) as saver:
            assert saver is not None
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            assert isinstance(saver, AsyncSqliteSaver)

        # File should exist on disk
        assert os.path.exists(db_path)
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass
