"""Unit tests for configuration validation and secret masking."""
import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_default_settings():
    """Verify default settings instantiation and types."""
    cfg = Settings(env="test")
    assert cfg.env == "test"
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8000
    assert cfg.max_agent_retries == 3
    assert cfg.docker_sandbox_enabled is True


def test_cors_origins_parsing():
    """Verify comma-separated and JSON string parsing for CORS origins."""
    cfg1 = Settings(cors_origins="http://example.com, https://app.example.com")
    assert cfg1.cors_origins == ["http://example.com", "https://app.example.com"]

    cfg2 = Settings(cors_origins='["http://localhost:3000", "http://localhost:8080"]')
    assert cfg2.cors_origins == ["http://localhost:3000", "http://localhost:8080"]


def test_settings_safe_dict_masks_secrets():
    """Verify safe_dict() masks sensitive credentials and database passwords."""
    cfg = Settings(
        gemini_api_key="AIzaSySecretGeminiKey1234567890",
        openai_api_key="sk-OpenAISecretKey9876543210",
        github_token="ghp_123456789012345678901234567890123456",
        database_url="postgresql+asyncpg://admin:supersecret@localhost:5432/devsquad",
    )
    safe = cfg.safe_dict()
    assert safe["gemini_api_key"] == "[CONFIGURED]"
    assert safe["openai_api_key"] == "[CONFIGURED]"
    assert safe["github_token"] == "[CONFIGURED]"
    assert "supersecret" not in safe["database_url"]
    assert "***@localhost:5432/devsquad" in safe["database_url"]


def test_settings_validation_limits():
    """Verify bounds enforcement on numeric settings."""
    with pytest.raises(ValidationError):
        Settings(docker_timeout_seconds=5)  # ge=10

    with pytest.raises(ValidationError):
        Settings(max_agent_retries=20)  # le=10
