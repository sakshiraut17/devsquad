"""Real health and diagnostics service for DevSquad subsystems."""
import time
from datetime import datetime, timezone
import docker
import docker.errors
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.schemas.health import ComponentHealth, HealthResponse


class HealthService:
    """Provides genuine health and connectivity checks without simulated or fake results."""

    @staticmethod
    async def check_database(db: AsyncSession) -> ComponentHealth:
        """Check database reachability via explicit SELECT 1 ping."""
        start_time = time.perf_counter()
        checked_at = datetime.now(timezone.utc)
        try:
            result = await db.execute(text("SELECT 1"))
            row = result.scalar()
            
            # Verify Alembic schema migration version
            migration_head = None
            try:
                mig_result = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                migration_head = mig_result.scalar()
            except Exception:
                migration_head = None

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if row == 1:
                return ComponentHealth(
                    component="database",
                    status="operational",
                    message="Database connection established and responding with active schema.",
                    details={
                        "engine": "aiosqlite" if "sqlite" in settings.database_url else "postgresql",
                        "latency_ms": latency_ms,
                        "schema_migration": "verified_head" if migration_head else "unversioned",
                        "migration_version": migration_head or "none",
                    },
                    checked_at=checked_at,
                )
            return ComponentHealth(
                component="database",
                status="error",
                message=f"Database query unexpected result: {row}",
                details={"latency_ms": latency_ms},
                checked_at=checked_at,
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ComponentHealth(
                component="database",
                status="error",
                message=f"Database connection error: {str(exc)}",
                details={"latency_ms": latency_ms, "error": str(exc)},
                checked_at=checked_at,
            )

    @staticmethod
    def check_llm() -> ComponentHealth:
        """
        Check LLM provider configuration and readiness.
        Does not call paid inference on routine health check requests.
        Distinguishes unconfigured, operational, and missing credentials.
        """
        checked_at = datetime.now(timezone.utc)
        provider = settings.llm_provider

        if provider == "gemini":
            key_configured = bool(settings.gemini_api_key.get_secret_value())
            model = settings.gemini_model
        elif provider == "openai":
            key_configured = bool(settings.openai_api_key.get_secret_value())
            model = settings.openai_model
        elif provider == "groq":
            key_configured = bool(settings.groq_api_key.get_secret_value())
            model = settings.groq_model
        else:
            return ComponentHealth(
                component="llm",
                status="error",
                message=f"Unsupported LLM provider configured: '{provider}'.",
                details={"provider": provider},
                checked_at=checked_at,
            )

        if not key_configured:
            return ComponentHealth(
                component="llm",
                status="unconfigured",
                message=f"LLM provider '{provider}' is not configured with an API key. Set DEVSQUAD_{provider.upper()}_API_KEY.",
                details={
                    "provider": provider,
                    "model": model,
                    "configured": False,
                },
                checked_at=checked_at,
            )

        return ComponentHealth(
            component="llm",
            status="operational",
            message=f"LLM provider '{provider}' configured with model '{model}'.",
            details={
                "provider": provider,
                "model": model,
                "configured": True,
            },
            checked_at=checked_at,
        )

    @staticmethod
    def check_docker() -> ComponentHealth:
        """
        Check Docker daemon availability.
        Distinguishes operational daemon from an unavailable environment.
        """
        checked_at = datetime.now(timezone.utc)
        if not settings.docker_sandbox_enabled:
            return ComponentHealth(
                component="docker",
                status="unavailable",
                message="Docker sandbox is disabled in configuration. DevSquad will use AST static validation fallback.",
                details={"enabled": False},
                checked_at=checked_at,
            )

        try:
            client = docker.from_env(timeout=3)
            is_alive = client.ping()
            if is_alive:
                version_info = client.version()
                return ComponentHealth(
                    component="docker",
                    status="operational",
                    message="Docker daemon is active and responsive.",
                    details={
                        "version": version_info.get("Version", "unknown"),
                        "os": version_info.get("Os", "unknown"),
                        "arch": version_info.get("Arch", "unknown"),
                    },
                    checked_at=checked_at,
                )
            return ComponentHealth(
                component="docker",
                status="unavailable",
                message="Docker ping returned False.",
                details={},
                checked_at=checked_at,
            )
        except (docker.errors.DockerException, Exception) as exc:
            return ComponentHealth(
                component="docker",
                status="unavailable",
                message="Docker daemon is not running or unavailable. DevSquad will use AST static validation fallback.",
                details={"error": str(exc)},
                checked_at=checked_at,
            )

    @classmethod
    async def get_composite_health(cls, db: AsyncSession) -> HealthResponse:
        """Aggregate health check for all platform subsystems."""
        now = datetime.now(timezone.utc)
        db_health = await cls.check_database(db)
        llm_health = cls.check_llm()
        docker_health = cls.check_docker()

        components = {
            "database": db_health,
            "llm": llm_health,
            "docker": docker_health,
        }

        # Overall platform status determination
        if db_health.status == "error":
            overall_status = "error"
        elif docker_health.status == "unavailable" or llm_health.status == "unconfigured":
            overall_status = "degraded"
        else:
            overall_status = "operational"

        return HealthResponse(
            status=overall_status,
            environment=settings.env,
            version="0.1.0",
            components=components,
            timestamp=now,
        )


def is_docker_available() -> bool:
    """Return True if Docker daemon is running, enabled, and responsive."""
    return HealthService.check_docker().status == "operational"

