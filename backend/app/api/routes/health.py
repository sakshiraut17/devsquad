"""Health check API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.health import ComponentHealth, HealthResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def get_health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Retrieve composite health of all subsystems (database, LLM readiness, Docker sandbox)."""
    return await HealthService.get_composite_health(db)


@router.get("/database", response_model=ComponentHealth)
async def get_database_health(db: AsyncSession = Depends(get_db)) -> ComponentHealth:
    """Check database reachability via explicit query execution."""
    return await HealthService.check_database(db)


@router.get("/llm", response_model=ComponentHealth)
async def get_llm_health() -> ComponentHealth:
    """Check LLM provider configuration and readiness without executing paid inference."""
    return HealthService.check_llm()


@router.get("/docker", response_model=ComponentHealth)
async def get_docker_health() -> ComponentHealth:
    """Check Docker daemon availability, reporting operational or honest fallback necessity."""
    return HealthService.check_docker()


@router.get("/security", response_model=ComponentHealth)
async def get_security_health() -> ComponentHealth:
    """Check AI Security Guardian status, active scanners, and blocking policy."""
    return HealthService.check_security_guardian()
