"""Security tests verifying secret redaction in exceptions and loggers."""
import logging
import pytest
from httpx import AsyncClient
from app.core.exceptions import SecurityViolationError
from app.core.logging import SecretRedactionFilter
from app.main import app


def test_logging_filter_redacts_tokens():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="Authentication failed for token ghp_ABCDEF1234567890abcdef12345678901234",
        args=(),
        exc_info=None,
    )
    redaction_filter = SecretRedactionFilter()
    redaction_filter.filter(record)
    assert "ghp_ABCDEF" not in record.msg
    assert "[REDACTED]" in record.msg


@pytest.mark.asyncio
async def test_exception_handler_redacts_secrets_in_responses(async_client: AsyncClient):
    # Dynamically mount a test route that raises a SecurityViolationError with a secret
    @app.get("/test-secret-leak")
    async def leak_route():
        raise SecurityViolationError(
            "Access denied for secret key sk-test1234567890abcdef1234567890"
        )

    response = await async_client.get("/test-secret-leak")
    assert response.status_code == 400
    data = response.json()
    assert "sk-test12345" not in data["message"]
    assert "[REDACTED]" in data["message"]
