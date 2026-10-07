from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.schemas.system import SystemStatusResponse
import docker

router = APIRouter()


@router.get("/system/status", response_model=SystemStatusResponse, tags=["System"])
async def get_system_status(db: AsyncSession = Depends(get_db)) -> SystemStatusResponse:
    """Detailed system status diagnostic endpoint checking DB, Docker, and LLM configuration."""
    
    # Check Database Connection
    db_connected = False
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_connected = True
    except Exception:
        db_connected = False

    # Check LLM Configuration
    llm_configured = False
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        llm_configured = True
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        llm_configured = True

    # Check Docker Availability
    docker_available = False
    try:
        client = docker.from_env()
        docker_available = client.ping()
    except Exception:
        docker_available = False

    overall_status = "operational" if (db_connected and llm_configured) else "degraded"

    return SystemStatusResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        database_connected=db_connected,
        database_engine=settings.async_database_url.split(":")[0],
        llm_provider=settings.LLM_PROVIDER,
        llm_configured=llm_configured,
        docker_available=docker_available,
        details={
            "debug_mode": settings.DEBUG,
            "cors_origins": settings.CORS_ORIGINS,
            "sandbox_image": settings.DOCKER_SANDBOX_IMAGE,
        },
    )
