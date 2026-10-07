from app.core.config import Settings


def test_settings_defaults():
    """Verify settings defaults are populated correctly."""
    settings = Settings()
    assert settings.PROJECT_NAME == "DevSquad AI Engineering Platform"
    assert settings.VERSION == "0.1.0"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.async_database_url.startswith("sqlite+aiosqlite") or settings.async_database_url.startswith("postgresql")
