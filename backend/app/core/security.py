"""DevSquad security utilities: secret redaction, path traversal checks, and hash verification."""
import hashlib
import os
import re
from pathlib import Path
from typing import Any

# Regex patterns for common sensitive tokens and keys
SENSITIVE_PATTERNS = [
    # GitHub Tokens (classic and fine-grained)
    re.compile(r"(ghp_[a-zA-Z0-9]{36,255}|github_pat_[a-zA-Z0-9_]{60,255})"),
    # Generic API Keys / Bearer tokens in headers or strings
    re.compile(r"(Bearer\s+)([a-zA-Z0-9_\-\.]{15,})", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[:=]\s*['\"]?)([a-zA-Z0-9_\-\.]{12,})(['\"]?)", re.IGNORECASE),
    re.compile(r"(secret\s*[:=]\s*['\"]?)([a-zA-Z0-9_\-\.]{12,})(['\"]?)", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*['\"]?)([^\s'\"]{6,})(['\"]?)", re.IGNORECASE),
    # OpenAI & Gemini key patterns
    re.compile(r"(sk-[a-zA-Z0-9]{20,})"),
    re.compile(r"(AIzaSy[a-zA-Z0-9_\-]{33})"),
]


def redact_secrets(text: str) -> str:
    """Redact known API keys, tokens, and passwords from text strings."""
    if not text:
        return text

    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        # Check if the pattern has multiple groups or single match
        def _replace_match(match: re.Match[str]) -> str:
            if match.lastindex and match.lastindex >= 2:
                prefix = match.group(1)
                suffix = match.group(3) if match.lastindex >= 3 else ""
                return f"{prefix}[REDACTED]{suffix}"
            return "[REDACTED]"

        sanitized = pattern.sub(_replace_match, sanitized)
    return sanitized


def compute_sha256(content: str) -> str:
    """Compute canonical SHA-256 hash for patch or artifact content."""
    normalized = content.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def is_safe_relative_path(path_str: str, base_dir: Path | None = None) -> bool:
    """
    Validate that a path string is safe, strictly relative, and does not escape base_dir.
    Rejects:
    - Absolute paths (e.g. /etc/passwd, C:\\Windows)
    - Path traversal components ('..')
    - Null bytes or control characters
    """
    if not path_str or "\x00" in path_str:
        return False

    raw_path = Path(path_str)

    # Must not be absolute
    if raw_path.is_absolute() or path_str.startswith("/") or path_str.startswith("\\"):
        return False

    # Check for drive letters (e.g. C:)
    if len(path_str) > 1 and path_str[1] == ":":
        return False

    # Check each part for traversal
    for part in raw_path.parts:
        if part in ("..", "~"):
            return False

    if base_dir is not None:
        try:
            resolved = (base_dir / raw_path).resolve()
            if not str(resolved).startswith(str(base_dir.resolve())):
                return False
        except (ValueError, RuntimeError):
            return False

    return True


def sanitize_dict_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask sensitive keys in dictionaries before logging."""
    sensitive_keys = {
        "api_key",
        "gemini_api_key",
        "openai_api_key",
        "github_token",
        "token",
        "secret",
        "password",
        "authorization",
    }
    sanitized: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in sensitive_keys:
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict_for_logging(v)
        elif isinstance(v, str):
            sanitized[k] = redact_secrets(v)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_dict_for_logging(item) if isinstance(item, dict)
                else (redact_secrets(item) if isinstance(item, str) else item)
                for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized


def create_access_token(
    user_id: str,
    email: str,
    secret_key: str | None = None,
    expires_in_seconds: int = 86400,
) -> str:
    """Generate a tamper-evident signed access token using HMAC-SHA256."""
    import base64
    import hmac
    import json
    import time
    from app.core.config import settings

    secret = secret_key or settings.secret_key.get_secret_value()
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    header_b64 = base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8")).decode("utf-8").rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("utf-8").rstrip("=")
    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_access_token(
    token: str,
    secret_key: str | None = None,
) -> dict[str, Any]:
    """Verify HMAC-SHA256 signature and expiration of an access token."""
    import base64
    import hmac
    import json
    import time
    from app.core.config import settings

    secret = secret_key or settings.secret_key.get_secret_value()
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format: must have 3 segments.")

    header_b64, payload_b64, sig_b64 = parts
    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()

    sig_padding = len(sig_b64) % 4
    padded_sig = sig_b64 + ("=" * ((4 - sig_padding) % 4))
    try:
        actual_sig = base64.urlsafe_b64decode(padded_sig.encode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid signature encoding.") from exc

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Token signature verification failed.")

    payload_padding = len(payload_b64) % 4
    padded_payload = payload_b64 + ("=" * ((4 - payload_padding) % 4))
    try:
        payload_data = json.loads(base64.urlsafe_b64decode(padded_payload.encode("utf-8")).decode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid payload encoding.") from exc

    now = int(time.time())
    if "exp" in payload_data and payload_data["exp"] < now:
        raise ValueError("Token has expired.")

    return payload_data


# In-memory tracking of consumed ticket JTIs for replay protection
_CONSUMED_STREAM_JTIS: dict[str, int] = {}


def create_stream_ticket(
    user_id: str,
    run_id: str,
    secret_key: str | None = None,
    expires_in_seconds: int = 60,
) -> str:
    """
    Generate a short-lived, tamper-evident stream ticket bound strictly to a user_id and run_id.
    Valid for 60 seconds by default. Eliminates long-lived bearer token exposure in URLs and server logs.
    """
    import base64
    import hmac
    import json
    import secrets
    import time
    from app.core.config import settings

    secret = secret_key or settings.secret_key.get_secret_value()
    header = {"alg": "HS256", "typ": "STREAM_TICKET"}
    now = int(time.time())
    payload = {
        "sub": user_id,
        "run_id": run_id,
        "purpose": "run_stream",
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    header_b64 = (
        base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        .decode("utf-8")
        .rstrip("=")
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        .decode("utf-8")
        .rstrip("=")
    )
    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_stream_ticket(
    ticket: str,
    expected_run_id: str,
    secret_key: str | None = None,
    consume: bool = True,
) -> dict[str, Any]:
    """
    Verify the signature, expiration, run binding, and replay status of a stream ticket.
    Raises ValueError if invalid, expired, mismatched run, or already consumed.
    """
    import base64
    import hmac
    import json
    import time
    from app.core.config import settings

    secret = secret_key or settings.secret_key.get_secret_value()
    parts = ticket.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid stream ticket format: must have 3 segments.")

    header_b64, payload_b64, sig_b64 = parts
    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()

    sig_padding = len(sig_b64) % 4
    padded_sig = sig_b64 + ("=" * ((4 - sig_padding) % 4))
    try:
        actual_sig = base64.urlsafe_b64decode(padded_sig.encode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid stream ticket signature encoding.") from exc

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Stream ticket signature verification failed.")

    payload_padding = len(payload_b64) % 4
    padded_payload = payload_b64 + ("=" * ((4 - payload_padding) % 4))
    try:
        payload_data = json.loads(base64.urlsafe_b64decode(padded_payload.encode("utf-8")).decode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid stream ticket payload encoding.") from exc

    if payload_data.get("purpose") != "run_stream":
        raise ValueError("Invalid ticket purpose: expected 'run_stream'.")

    now = int(time.time())
    if "exp" in payload_data and payload_data["exp"] < now:
        raise ValueError("Stream ticket has expired.")

    if payload_data.get("run_id") != expected_run_id:
        raise ValueError(f"Stream ticket run mismatch: ticket is not valid for run {expected_run_id}.")

    # Replay protection check
    jti = payload_data.get("jti")
    if jti:
        # Prune expired JTIs
        expired_jtis = [k for k, exp in _CONSUMED_STREAM_JTIS.items() if exp < now]
        for k in expired_jtis:
            _CONSUMED_STREAM_JTIS.pop(k, None)

        if jti in _CONSUMED_STREAM_JTIS:
            raise ValueError("Stream ticket has already been used (replay detected).")

        if consume:
            _CONSUMED_STREAM_JTIS[jti] = payload_data.get("exp", now + 60)

    return payload_data


