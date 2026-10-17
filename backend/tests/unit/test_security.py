"""Unit tests for security utilities: redaction, hashing, and path traversal."""
from pathlib import Path
from app.core.security import (
    compute_sha256,
    is_safe_relative_path,
    redact_secrets,
    sanitize_dict_for_logging,
)


def test_redact_github_tokens():
    raw = "Failed with token ghp_123456789012345678901234567890123456 in request"
    redacted = redact_secrets(raw)
    assert "ghp_" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_openai_and_gemini_keys():
    raw_openai = "sk-1234567890abcdef1234567890 is the key"
    assert "sk-123456" not in redact_secrets(raw_openai)
    assert "[REDACTED]" in redact_secrets(raw_openai)

    raw_gemini = "AIzaSyABCDEF1234567890abcdef12345678901"
    assert "AIzaSy" not in redact_secrets(raw_gemini)
    assert "[REDACTED]" in redact_secrets(raw_gemini)


def test_redact_bearer_tokens_and_passwords():
    raw_bearer = "Authorization: Bearer mySecretToken1234567890"
    assert "mySecretToken" not in redact_secrets(raw_bearer)

    raw_pwd = 'password: "superSecretPassword123"'
    assert "superSecretPassword123" not in redact_secrets(raw_pwd)


def test_compute_sha256_canonical():
    crlf_text = "line1\r\nline2\r\n"
    lf_text = "line1\nline2\n"
    assert compute_sha256(crlf_text) == compute_sha256(lf_text)
    assert len(compute_sha256("test")) == 64


def test_is_safe_relative_path():
    # Safe relative paths
    assert is_safe_relative_path("src/main.py") is True
    assert is_safe_relative_path("tests/unit/test_app.py") is True
    assert is_safe_relative_path("README.md") is True

    # Traversal attempts
    assert is_safe_relative_path("../etc/passwd") is False
    assert is_safe_relative_path("src/../../secret.txt") is False
    assert is_safe_relative_path("~/.ssh/id_rsa") is False

    # Absolute paths
    assert is_safe_relative_path("/etc/passwd") is False
    assert is_safe_relative_path("\\Windows\\System32") is False
    assert is_safe_relative_path("C:\\Users\\admin\\file.txt") is False

    # Null byte attack
    assert is_safe_relative_path("src/main.py\x00.exe") is False


def test_sanitize_dict_for_logging():
    log_data = {
        "user": "developer",
        "github_token": "ghp_secrettoken12345678901234567890123456",
        "nested": {
            "api_key": "secret123456789",
            "message": "Authorization failed with Bearer secretBearerToken123456",
        },
    }
    sanitized = sanitize_dict_for_logging(log_data)
    assert sanitized["github_token"] == "[REDACTED]"
    assert sanitized["nested"]["api_key"] == "[REDACTED]"
    assert "secretBearerToken" not in sanitized["nested"]["message"]
