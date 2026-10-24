"""DevSquad API v1 Central Router."""
from fastapi import APIRouter
from app.api.routes import auth, github, health, issues, overview, repositories, runs

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(overview.router)
api_router.include_router(health.router)
api_router.include_router(repositories.router)
api_router.include_router(issues.router)
api_router.include_router(runs.router)
api_router.include_router(github.router)
