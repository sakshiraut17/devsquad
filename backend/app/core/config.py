from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DevSquad Global Configuration Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Server Configuration
    PROJECT_NAME: str = "DevSquad AI Engineering Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # PostgreSQL / SQLite Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "devsquad_user"
    POSTGRES_PASSWORD: str = "devsquad_password_secure"
    POSTGRES_DB: str = "devsquad_db"
    DATABASE_URL: Optional[str] = None

    @property
    def async_database_url(self) -> str:
        """Return full async database URL, defaulting to SQLite async if Postgres URL is not set."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"sqlite+aiosqlite:///./devsquad.db"

    # LLM Provider Configuration
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    DEFAULT_MODEL: str = "gemini-1.5-pro"

    # GitHub OAuth / Token Configuration
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_PERSONAL_ACCESS_TOKEN: Optional[str] = None

    # Security Configuration
    SECRET_KEY: str = "devsquad-insecure-secret-key-change-in-production-12345"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520  # 8 days

    # Docker Sandbox Parameters
    DOCKER_SANDBOX_IMAGE: str = "devsquad-sandbox:latest"
    DOCKER_CONTAINER_CPU_LIMIT: float = 1.0
    DOCKER_CONTAINER_MEMORY_LIMIT: str = "512m"
    DOCKER_EXECUTION_TIMEOUT_SECONDS: int = 60


settings = Settings()
