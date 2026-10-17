"""Pytest configuration and async test fixtures using an isolated temporary SQLite database."""
import os
import tempfile
from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.db.base import Base
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an isolated temporary SQLite database for each test function."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    test_db_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(test_db_url, connect_args={"check_same_thread": False})

    # Enforce SQLite foreign keys and WAL mode for concurrency
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    import unittest.mock
    with unittest.mock.patch("app.db.session.async_session_factory", session_factory), \
         unittest.mock.patch("app.api.routes.runs.async_session_factory", session_factory):
        async with session_factory() as session:
            yield session

    await engine.dispose()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest_asyncio.fixture(scope="function")
async def default_user(test_db_session: AsyncSession) -> User:
    """Create a default active User in the test database."""
    user = User(
        id="00000000-0000-0000-0000-000000000001",
        email="developer@devsquad.ai",
        display_name="Dev Squad Developer",
        is_active=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
def auth_headers(default_user: User) -> dict[str, str]:
    """Generate valid Bearer Authorization headers for the default user."""
    token = create_access_token(user_id=default_user.id, email=default_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def async_client(
    test_db_session: AsyncSession,
    default_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP async client authenticated as default_user with get_db overridden."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(user_id=default_user.id, email=default_user.email)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=headers) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def unauthenticated_client(
    test_db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP async client without any authorization headers."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def mock_agents():
    """Mock multi-agent services for orchestration testing."""
    from unittest.mock import AsyncMock, MagicMock
    from app.schemas.plan import PlanStep, StructuredPlan
    from app.schemas.patch import PatchItem
    from app.schemas.test_result import TestResult
    from app.schemas.review import ReviewFinding, ReviewResponse

    planner = MagicMock()
    plan = StructuredPlan(
        objective="Fix math bug",
        problem_summary="Subtract bug",
        steps=[PlanStep(id="1", description="Fix op", target_files=["calc.py"], rationale="Fix")],
        acceptance_criteria=["calc works"],
        required_tests=["tests/test_calc.py"],
        risks=[],
        assumptions=[],
        uncertainties=[],
    )
    planner.plan = AsyncMock(return_value=plan)

    coder = MagicMock()
    patch = PatchItem(
        unified_diff="--- a/calc.py\n+++ b/calc.py\n@@ -1,1 +1,1 @@\n-a+b\n+a-b\n",
        target_files=["calc.py"],
        base_commit_sha="sha123",
        file_hashes={"calc.py": "hash1"},
        summary="Fix subtraction",
        revision=1,
        content_hash="contenthash123",
    )
    coder.generate_patch = AsyncMock(return_value=patch)

    tester = MagicMock()
    test_res = TestResult(
        status="PARTIAL_VALIDATION",
        environment="host_ast_fallback",
        commands_executed=["ast.parse"],
        exit_code=0,
        passed=1,
        failed=0,
        skipped=0,
        stdout="AST passed",
        stderr="",
        duration_ms=15,
    )
    tester.run_tests = AsyncMock(return_value=test_res)

    reviewer = MagicMock()
    rev_res = ReviewResponse(
        findings=[ReviewFinding(
            id="F1",
            severity="INFO",
            category="style",
            file_path="calc.py",
            line_number=1,
            description="Clean code",
            evidence="looks good",
            recommendation="keep",
        )],
        acceptance_criteria_met=True,
        recommendation="approve",
        unresolved_risks=[],
    )
    reviewer.review = AsyncMock(return_value=rev_res)

    return planner, coder, tester, reviewer
