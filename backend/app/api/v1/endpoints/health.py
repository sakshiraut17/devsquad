from fastapi import APIRouter
from app.core.config import settings
from app.schemas.system import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Basic health check endpoint returning system version and timestamp."""
    return HealthResponse(
        status="healthy",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
    )
