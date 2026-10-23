"""Deterministic Secret and Credential Exposure Scanner for DevSquad AI Security Guardian."""

import hashlib
import re
from typing import List, Optional, Tuple
from app.schemas.security import SecurityCategory, SecurityFindingSchema, SecuritySeverity


# Compiled regex patterns for high-confidence credentials and secrets
SECRET_PATTERNS: List[Tuple[str, str, str, re.Pattern]] = [
    (
        "SEC-001",
        "OpenAI API Key Exposure",
        "OpenAI API key detected in code patch.",
        re.compile(r"(?:sk-[a-zA-Z0-9]{20,}|sk-proj-[a-zA-Z0-9_\-]{30,})"),
    ),
    (
        "SEC-002",
        "Groq API Key Exposure",
        "Groq API key detected in code patch.",
        re.compile(r"gsk_[a-zA-Z0-9]{20,}"),
    ),
    (
        "SEC-003",
        "GitHub Access Token Exposure",
        "GitHub personal access token or OAuth key detected.",
        re.compile(r"(?:ghp_[a-zA-Z0-9]{20,}|gho_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{22,})"),
    ),
    (
        "SEC-004",
        "AWS Access Key ID Exposure",
        "Amazon Web Services access key ID detected.",
        re.compile(r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}"),
    ),
    (
        "SEC-005",
        "Google Cloud / Gemini API Key Exposure",
        "Google Cloud Platform or Gemini API key detected.",
        re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    ),
    (
        "SEC-006",
        "Stripe Secret Key Exposure",
        "Stripe live API key or restricted key detected.",
        re.compile(r"(?:sk_live|rk_live)_[0-9a-zA-Z]{24,}"),
    ),
    (
        "SEC-007",
        "Slack Token Exposure",
        "Slack bot or user token detected.",
        re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,}"),
    ),
    (
        "SEC-008",
        "Private Cryptographic Key Exposure",
        "Unencrypted private cryptographic key block detected.",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    ),
    (
        "SEC-009",
        "Database Connection String With Password",
        "Database URI containing embedded plaintext user password.",
        re.compile(r"(?:postgres|postgresql|mysql|mongodb|redis):\/\/[a-zA-Z0-9_\-\.]+:[^@\s\/'\"]{4,}@[a-zA-Z0-9_\-\.]+"),
    ),
    (
        "SEC-010",
        "Hardcoded Secret Assignment",
        "High-entropy secret or password assigned directly in code.",
        re.compile(r"""(?:password|passwd|api_key|access_token|secret_key|auth_token)\s*=\s*['"]([A-Za-z0-9_\-+/]{16,})['"]""", re.IGNORECASE),
    ),
]

# Patterns for obvious safe test placeholders to minimize false positives
BENIGN_PLACEHOLDER_REGEX = re.compile(
    r"(?:your[-_]api[-_]key|placeholder|example|dummy|fake|test[-_]token|none|env\(\)|os\.environ|get_secret_value|<.*?>|\$\{.+\})",
    re.IGNORECASE,
)


def redact_secret_string(value: str) -> Tuple[str, str]:
    """Deterministically redact a secret string using a SHA-256 fingerprint.

    Returns:
        (redacted_representation, sha256_fingerprint)
    """
    secret_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    prefix = value[:4] if len(value) >= 8 and not value.startswith("-----") else ""
    redacted = f"{prefix}***[REDACTED_SECRET:{secret_hash[:8]}]***"
    return redacted, secret_hash


class SecretScanner:
    """Scans code patches and unified diffs for sensitive credentials and private keys."""

    def __init__(self, scanner_version: str = "1.0.0"):
        self.version = scanner_version

    def scan_diff(
        self,
        unified_diff: str,
        run_id: str,
        patch_revision: int,
        patch_hash: str,
        base_commit_sha: Optional[str] = None,
    ) -> List[SecurityFindingSchema]:
        """Inspect added and modified lines within a unified diff."""
        findings: List[SecurityFindingSchema] = []
        if not unified_diff:
            return findings

        current_file = "unknown"
        current_line_no = 0

        for line in unified_diff.splitlines():
            # Track target file header
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                continue
            elif line.startswith("+++ "):
                current_file = line[4:].strip()
                continue

            # Track chunk line numbers: @@ -1,4 +1,6 @@
            if line.startswith("@@ "):
                match = re.search(r"\+(\d+)(?:,\d+)? @@", line)
                if match:
                    current_line_no = int(match.group(1)) - 1
                continue

            # We only scan added lines ('+') and ignore diff metadata ('+++')
            if line.startswith("+") and not line.startswith("+++"):
                current_line_no += 1
                added_content = line[1:].strip()

                # Skip blank lines and short comments
                if not added_content or (added_content.startswith("#") and len(added_content) < 15):
                    continue

                for rule_id, title, desc, pattern in SECRET_PATTERNS:
                    match = pattern.search(added_content)
                    if match:
                        matched_str = match.group(0)

                        # Filter obvious dummy placeholders
                        if BENIGN_PLACEHOLDER_REGEX.search(matched_str) or "localhost" in matched_str:
                            continue

                        redacted_val, fingerprint = redact_secret_string(matched_str)
                        safe_line = added_content.replace(matched_str, redacted_val)

                        findings.append(
                            SecurityFindingSchema(
                                run_id=run_id,
                                patch_revision=patch_revision,
                                patch_hash=patch_hash,
                                base_commit_sha=base_commit_sha,
                                category=SecurityCategory.SECRET_EXPOSURE.value,
                                rule_id=rule_id,
                                title=title,
                                description=f"{desc} (Fingerprint: {fingerprint[:8]}…)",
                                severity=SecuritySeverity.CRITICAL.value,
                                confidence="HIGH",
                                file_path=current_file,
                                line_start=current_line_no,
                                line_end=current_line_no,
                                evidence_redacted=safe_line,
                                remediation="Remove hardcoded credential. Use environment variables (e.g. settings or os.environ) instead.",
                                scanner_name="secret_scanner",
                                scanner_version=self.version,
                                is_blocking=True,
                                status="ACTIVE",
                            )
                        )
            elif not line.startswith("-"):
                current_line_no += 1

        return findings
