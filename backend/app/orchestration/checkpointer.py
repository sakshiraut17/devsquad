"""Persistent LangGraph checkpointing infrastructure using AsyncSqliteSaver."""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator, Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = logging.getLogger("devsquad.checkpointer")

DEFAULT_CHECKPOINT_DB_PATH = "devsquad_checkpoints.db"


@asynccontextmanager
async def get_async_checkpointer(
    db_path: Optional[str] = None,
) -> AsyncGenerator[BaseCheckpointSaver, None]:
    """Provide an initialized persistent AsyncSqliteSaver or ephemeral InMemorySaver.
    
    If db_path == ":memory:", returns an InMemorySaver (ideal for fast isolated tests).
    Otherwise, returns an AsyncSqliteSaver backed by a SQLite database file.
    """
    target_path = db_path or DEFAULT_CHECKPOINT_DB_PATH

    if target_path == ":memory:":
        logger.debug("Using InMemorySaver checkpointer for ephemeral execution.")
        yield InMemorySaver()
    else:
        logger.debug(f"Opening persistent AsyncSqliteSaver at '{target_path}'.")
        async with AsyncSqliteSaver.from_conn_string(target_path) as saver:
            yield saver
