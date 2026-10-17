"""DevSquad centralized application configuration with Pydantic V2 Settings."""
import json
from pathlib import Path
from typing import Any, Literal, Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration for DevSquad backend."""

    model_config = SettingsConfigDict(
        env_prefix="DEVSQUAD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Environment
    env: Literal["development", "staging", "production", "test"] = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    secret_key: SecretStr = SecretStr("devsquad-insecure-secret-key-change-in-production")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database Configuration (SQLite aiosqlite locally, asyncpg for PostgreSQL)
    database_url: str = "sqlite+aiosqlite:///./devsquad.db"

    # LLM Providers Configuration
    llm_provider: Literal["gemini", "openai", "groq"] = "gemini"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o"
    openai_base_url: Optional[str] = None
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # GitHub Integration
    github_token: SecretStr = SecretStr("")
    github_api_url: str = "https://api.github.com"

    # Docker Sandbox Configuration
    docker_sandbox_enabled: bool = True
    docker_timeout_seconds: int = Field(default=120, ge=10, le=600)
    docker_memory_limit: str = "1g"
    docker_cpu_limit: float = Field(default=1.0, gt=0.0, le=8.0)
    allow_manual_approval_without_sandbox: bool = True

    # Workflow & Safety Limits
    max_agent_retries: int = Field(default=3, ge=1, le=10)
    max_patch_size_bytes: int = Field(default=1048576, ge=1024)  # 1MB
    max_repo_context_bytes: int = Field(default=5242880, ge=1024)  # 5MB
    max_run_duration_seconds: int = Field(default=3600, ge=60)  # 1 hour default

    @field_validator("database_url", mode="after")
    @classmethod
    def resolve_sqlite_path(cls, value: str) -> str:
        """Anchor relative SQLite paths to the canonical backend directory regardless of process CWD."""
        if value.startswith("sqlite") and ":///" in value and ":memory:" not in value:
            prefix, path_part = value.split(":///", 1)
            p = Path(path_part)
            if not p.is_absolute():
                backend_dir = Path(__file__).resolve().parent.parent.parent
                canonical = (backend_dir / p).resolve()
                return f"{prefix}:///{canonical.as_posix()}"
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def safe_dict(self) -> dict[str, Any]:
        """Return configuration as a dictionary with all secrets masked."""
        data = self.model_dump()
        # Explicitly mask secrets
        data["gemini_api_key"] = "[CONFIGURED]" if self.gemini_api_key.get_secret_value() else "[NOT CONFIGURED]"
        data["openai_api_key"] = "[CONFIGURED]" if self.openai_api_key.get_secret_value() else "[NOT CONFIGURED]"
        data["github_token"] = "[CONFIGURED]" if self.github_token.get_secret_value() else "[NOT CONFIGURED]"
        data["secret_key"] = "[CONFIGURED]" if self.secret_key.get_secret_value() else "[NOT CONFIGURED]"
        # Redact database password if postgresql url with credentials
        if "@" in self.database_url:
            parts = self.database_url.split("@")
            data["database_url"] = f"***@{parts[-1]}"
        return data


# Global singleton settings instance
settings = Settings()


def get_settings() -> Settings:
    """Return the global Settings instance."""
    return settings
