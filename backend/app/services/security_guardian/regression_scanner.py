"""Security Regression and Patch-Scope Inspector for DevSquad AI Security Guardian."""

import re
from typing import List, Optional, Set
from app.schemas.security import SecurityCategory, SecurityFindingSchema, SecuritySeverity

# Sensitive security control patterns whose deletion or weakening constitutes a security regression
PROTECTED_SECURITY_CONTROLS = [
    ("REG-001", "Depends(get_current_user)", "Removal of authentication dependency on API route."),
    ("REG-002", "verify_stream_ticket", "Removal or bypass of short-lived stream ticket verification."),
    ("REG-003", "is_safe_relative_path", "Removal of path traversal boundary validation."),
    ("REG-004", "SecretRedactionFilter", "Removal of logging secret redaction filter."),
    ("REG-005", "verify_plan_evidence", "Removal or bypass of cryptographic plan evidence verification."),
    ("REG-006", "patch.content_hash !=", "Weakening or removal of cryptographic patch hash verification in approval gate."),
    ("REG-007", "RunStatus.AWAITING_APPROVAL", "Tampering with approval status check in approval gate."),
]

# Sensitive configuration files that an automated patch must never touch
PROTECTED_SYSTEM_PATHS: Set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.txt",
    ".git",
    ".gitignore",
    ".github/workflows",
    "backend/alembic.ini",
}


class SecurityRegressionScanner:
    """Inspects unified diffs for attempts to weaken or bypass existing platform security controls."""

    def __init__(self, scanner_version: str = "1.0.0"):
        self.version = scanner_version

    def scan_diff(
        self,
        unified_diff: str,
        target_files: List[str],
        run_id: str,
        patch_revision: int,
        patch_hash: str,
        base_commit_sha: Optional[str] = None,
    ) -> List[SecurityFindingSchema]:
        """Inspect removed lines and target file paths for security regressions and scope violations."""
        findings: List[SecurityFindingSchema] = []
        if not unified_diff:
            return findings

        # 1. Patch Scope Guard: Check for unauthorized modifications to protected system files
        for target in target_files:
            clean_target = target.replace("\\", "/").strip().lstrip("/")
            for protected in PROTECTED_SYSTEM_PATHS:
                if clean_target == protected or clean_target.startswith(f"{protected}/"):
                    findings.append(
                        SecurityFindingSchema(
                            run_id=run_id,
                            patch_revision=patch_revision,
                            patch_hash=patch_hash,
                            base_commit_sha=base_commit_sha,
                            category=SecurityCategory.PATCH_SCOPE.value,
                            rule_id="SCOPE-001",
                            title="Prohibited System Configuration File Modification",
                            description=f"Patch attempts to modify protected system path '{target}' outside authorized scope.",
                            severity=SecuritySeverity.CRITICAL.value,
                            confidence="HIGH",
                            file_path=target,
                            evidence_redacted=f"Target file: {target}",
                            remediation="Do not modify repository infrastructure, environment, or Git configuration files in code patches.",
                            scanner_name="regression_scanner",
                            scanner_version=self.version,
                            is_blocking=True,
                            status="ACTIVE",
                        )
                    )

        # 2. Security Control Regression: Check removed lines
        current_file = "unknown"
        current_line_no = 0

        for line in unified_diff.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                continue
            elif line.startswith("+++ "):
                current_file = line[4:].strip()
                continue

            if line.startswith("@@ "):
                match = re.search(r"\+(\d+)(?:,\d+)? @@", line)
                if match:
                    current_line_no = int(match.group(1)) - 1
                continue

            # Check lines removed by the patch ('-')
            if line.startswith("-") and not line.startswith("---"):
                current_line_no += 1
                removed_code = line[1:].strip()

                for rule_id, pattern_str, reason in PROTECTED_SECURITY_CONTROLS:
                    if pattern_str in removed_code:
                        findings.append(
                            SecurityFindingSchema(
                                run_id=run_id,
                                patch_revision=patch_revision,
                                patch_hash=patch_hash,
                                base_commit_sha=base_commit_sha,
                                category=SecurityCategory.SECURITY_REGRESSION.value,
                                rule_id=rule_id,
                                title=f"Security Control Regression ({pattern_str})",
                                description=f"Patch removes or modifies security enforcement control: {reason}",
                                severity=SecuritySeverity.CRITICAL.value,
                                confidence="HIGH",
                                file_path=current_file,
                                line_start=current_line_no,
                                line_end=current_line_no,
                                evidence_redacted=removed_code,
                                remediation="Preserve mandatory security checks, authenticated dependencies, and validation filters.",
                                scanner_name="regression_scanner",
                                scanner_version=self.version,
                                is_blocking=True,
                                status="ACTIVE",
                            )
                        )

                # Check if security test assertions were deleted
                if "tests/security/" in current_file and removed_code.startswith("assert "):
                    findings.append(
                        SecurityFindingSchema(
                            run_id=run_id,
                            patch_revision=patch_revision,
                            patch_hash=patch_hash,
                            base_commit_sha=base_commit_sha,
                            category=SecurityCategory.SECURITY_REGRESSION.value,
                            rule_id="REG-010",
                            title="Security Test Assertion Deleted",
                            description="Patch deleted an assertion inside a security test file.",
                            severity=SecuritySeverity.HIGH.value,
                            confidence="HIGH",
                            file_path=current_file,
                            line_start=current_line_no,
                            line_end=current_line_no,
                            evidence_redacted=removed_code,
                            remediation="Security regression tests must not be weakened or removed.",
                            scanner_name="regression_scanner",
                            scanner_version=self.version,
                            is_blocking=True,
                            status="ACTIVE",
                        )
                    )
            elif not line.startswith("+"):
                current_line_no += 1

        return findings
