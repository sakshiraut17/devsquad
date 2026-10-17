"""DevSquad FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import DevSquadException
from app.core.logging import setup_logging
from app.core.security import redact_secrets
from app.db.session import close_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager managing startup and graceful shutdown."""
    # Startup
    setup_logging(settings.log_level)
    from app.db.session import async_session_factory
    from app.orchestration import get_orchestrator
    import logging

    startup_logger = logging.getLogger("devsquad.startup")
    try:
        async with async_session_factory() as session:
            orchestrator = get_orchestrator()
            reconciled = await orchestrator.reconcile_orphaned_runs(session)
            if reconciled:
                startup_logger.info(
                    f"Startup reconciliation: marked {len(reconciled)} orphaned run(s) as FAILED: {reconciled}"
                )
    except Exception as exc:
        startup_logger.warning(f"Startup orphan reconciliation skipped or failed: {exc}")

    yield
    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="DevSquad API",
        description="Production-Grade Multi-Agent AI Software Engineering Platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API v1 routes
    app.include_router(api_router)

    # Exception Handlers
    @app.exception_handler(DevSquadException)
    async def devsquad_exception_handler(request: Request, exc: DevSquadException) -> JSONResponse:
        sanitized_msg = redact_secrets(exc.message)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.__class__.__name__, "message": sanitized_msg, "details": exc.details},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        sanitized_msg = redact_secrets(str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "InternalServerError", "message": sanitized_msg},
        )

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": "DevSquad API",
            "version": "0.1.0",
            "docs_url": "/docs",
            "health_url": "/api/v1/health",
        }

    return app


app = create_app()
