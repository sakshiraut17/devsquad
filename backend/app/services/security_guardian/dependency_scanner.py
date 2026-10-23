"""Deterministic Dependency Vulnerability Auditor for DevSquad AI Security Guardian."""

import json
import logging
import re
from typing import Dict, List, Optional
from app.schemas.security import SecurityCategory, SecurityFindingSchema, SecuritySeverity

logger = logging.getLogger("devsquad.security.dependency_scanner")

# Known insecure/deprecated packages or patterns with critical CVEs
INSECURE_DEPENDENCIES = {
    "pycrypto": {
        "rule_id": "DEP-001",
        "title": "Vulnerable Package (pycrypto)",
        "description": "pycrypto is unmaintained and contains multiple unpatched critical vulnerabilities.",
        "severity": SecuritySeverity.CRITICAL.value,
        "remediation": "Replace pycrypto with cryptography or pycryptodome.",
    },
    "pickle5": {
        "rule_id": "DEP-002",
        "title": "Insecure Backport Package (pickle5)",
        "description": "pickle5 provides unconstrained deserialization.",
        "severity": SecuritySeverity.HIGH.value,
        "remediation": "Use built-in pickle with restricted dispatchers or modern formats like JSON.",
    },
    "telnetlib": {
        "rule_id": "DEP-003",
        "title": "Insecure Protocol Client (telnetlib)",
        "description": "telnetlib transmits plaintext credentials over network connections.",
        "severity": SecuritySeverity.HIGH.value,
        "remediation": "Use SSH or encrypted TLS protocols.",
    },
}


class DependencyAuditor:
    """Inspects project dependency manifests and lockfiles for known security risks."""

    def __init__(self, scanner_version: str = "1.0.0"):
        self.version = scanner_version

    def audit_manifest(
        self,
        file_path: str,
        content: str,
        run_id: str,
        patch_revision: int,
        patch_hash: str,
        base_commit_sha: Optional[str] = None,
    ) -> List[SecurityFindingSchema]:
        """Audit pyproject.toml, requirements.txt, or package.json."""
        findings: List[SecurityFindingSchema] = []
        filename = file_path.split("/")[-1].split("\\")[-1]

        # 1. Audit Python dependencies in requirements.txt or pyproject.toml
        if filename in ("requirements.txt", "pyproject.toml"):
            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("#"):
                    continue

                # Check insecure index URL (HTTP instead of HTTPS)
                if clean_line.startswith(("--index-url", "--extra-index-url", "index-url")) and "http://" in clean_line:
                    findings.append(
                        SecurityFindingSchema(
                            run_id=run_id,
                            patch_revision=patch_revision,
                            patch_hash=patch_hash,
                            base_commit_sha=base_commit_sha,
                            category=SecurityCategory.DEPENDENCY_AUDIT.value,
                            rule_id="DEP-010",
                            title="Insecure Plaintext Package Repository",
                            description=f"Package repository configured with unencrypted http:// URL: '{clean_line}'",
                            severity=SecuritySeverity.CRITICAL.value,
                            confidence="HIGH",
                            file_path=file_path,
                            line_start=idx,
                            line_end=idx,
                            evidence_redacted=clean_line,
                            remediation="Use secure HTTPS package repository URLs (e.g. https://pypi.org/simple).",
                            scanner_name="dependency_auditor",
                            scanner_version=self.version,
                            is_blocking=True,
                            status="ACTIVE",
                        )
                    )

                # Check known dangerous/deprecated packages
                for pkg, info in INSECURE_DEPENDENCIES.items():
                    if re.search(rf"\b{re.escape(pkg)}\b", clean_line, re.IGNORECASE):
                        findings.append(
                            SecurityFindingSchema(
                                run_id=run_id,
                                patch_revision=patch_revision,
                                patch_hash=patch_hash,
                                base_commit_sha=base_commit_sha,
                                category=SecurityCategory.DEPENDENCY_AUDIT.value,
                                rule_id=info["rule_id"],
                                title=info["title"],
                                description=info["description"],
                                severity=info["severity"],
                                confidence="HIGH",
                                file_path=file_path,
                                line_start=idx,
                                line_end=idx,
                                evidence_redacted=clean_line,
                                remediation=info["remediation"],
                                scanner_name="dependency_auditor",
                                scanner_version=self.version,
                                is_blocking=info["severity"] in (SecuritySeverity.CRITICAL.value, SecuritySeverity.HIGH.value),
                                status="ACTIVE",
                            )
                        )

                # Check unpinned wildcard dependencies in requirements: e.g. "requests==*", "requests=*", or "flask=*"
                if re.search(r"^[a-zA-Z0-9_\-]+\s*(?:==|>=|=)?\s*\*", clean_line):
                    findings.append(
                        SecurityFindingSchema(
                            run_id=run_id,
                            patch_revision=patch_revision,
                            patch_hash=patch_hash,
                            base_commit_sha=base_commit_sha,
                            category=SecurityCategory.DEPENDENCY_AUDIT.value,
                            rule_id="DEP-020",
                            title="Unbounded Wildcard Dependency Specification",
                            description=f"Dependency specified with wildcard version: '{clean_line}'",
                            severity=SecuritySeverity.MEDIUM.value,
                            confidence="HIGH",
                            file_path=file_path,
                            line_start=idx,
                            line_end=idx,
                            evidence_redacted=clean_line,
                            remediation="Pin dependency to explicit, audited semantic versions (e.g. >=2.31.0,<3.0.0).",
                            scanner_name="dependency_auditor",
                            scanner_version=self.version,
                            is_blocking=False,
                            status="ACTIVE",
                        )
                    )

        # 2. Audit Node.js package.json
        elif filename == "package.json":
            try:
                pkg_data = json.loads(content)
                for dep_type in ("dependencies", "devDependencies"):
                    deps = pkg_data.get(dep_type, {})
                    if isinstance(deps, dict):
                        for dep_name, version in deps.items():
                            if str(version).strip() == "*":
                                findings.append(
                                    SecurityFindingSchema(
                                        run_id=run_id,
                                        patch_revision=patch_revision,
                                        patch_hash=patch_hash,
                                        base_commit_sha=base_commit_sha,
                                        category=SecurityCategory.DEPENDENCY_AUDIT.value,
                                        rule_id="DEP-021",
                                        title=f"Wildcard Node Dependency ({dep_name})",
                                        description=f"Package '{dep_name}' uses unpinned wildcard version '*'.",
                                        severity=SecuritySeverity.MEDIUM.value,
                                        confidence="HIGH",
                                        file_path=file_path,
                                        evidence_redacted=f'"{dep_name}": "*"',
                                        remediation="Pin package to explicit semver range.",
                                        scanner_name="dependency_auditor",
                                        scanner_version=self.version,
                                        is_blocking=False,
                                        status="ACTIVE",
                                    )
                                )
            except json.JSONDecodeError:
                pass

        return findings
