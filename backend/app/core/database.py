from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from app.core.logging import logger

# Create SQLAlchemy Async Engine
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    future=True,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining async database sessions in FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rollback triggered due to error: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables if they do not exist."""
    async with engine.begin() as conn:
        # Import models here to ensure they are registered with Base.metadata
        from app.db.models import user, repository, issue, run, agent_log, patch, test_result, pull_request  # noqa: F401

        logger.info("Initializing database schema...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")
