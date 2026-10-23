"""AI Security Guardian Master Service coordinating multi-category security verification."""

from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_log import AgentLog
from app.db.models.security_finding import SecurityFinding
from app.db.models.security_scan_record import SecurityScanRecord
from app.db.session import async_session_factory
from app.schemas.patch import PatchItem
from app.schemas.security import (
    ScannerStatusItem,
    SecurityDiagnostics,
    SecurityFindingSchema,
    SecurityGateStatus,
    SecurityScanResult,
    SecuritySummary,
)
from app.services.security_guardian.dependency_scanner import DependencyAuditor
from app.services.security_guardian.policy_engine import SecurityPolicyEngine
from app.services.security_guardian.regression_scanner import SecurityRegressionScanner
from app.services.security_guardian.secret_scanner import SecretScanner
from app.services.security_guardian.source_scanner import SourceCodeScanner

logger = logging.getLogger("devsquad.security.guardian")


class SecurityGuardianService:
    """Production AI Security Guardian orchestrating multi-layer static and deterministic patch verification."""

    def __init__(
        self,
        session_factory: Optional[Callable[[], AsyncSession]] = None,
        policy_version: str = "1.0.0",
    ):
        self.session_factory = session_factory or async_session_factory
        self.policy_version = policy_version
        self.secret_scanner = SecretScanner()
        self.source_scanner = SourceCodeScanner()
        self.dependency_auditor = DependencyAuditor()
        self.regression_scanner = SecurityRegressionScanner()
        self.policy_engine = SecurityPolicyEngine(policy_version=policy_version)

    async def scan_patch(
        self,
        patch: PatchItem,
        run_id: str,
        source_files: Optional[Dict[str, str]] = None,
        base_commit_sha: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> SecurityScanResult:
        """Execute all security scanners on a patch revision, evaluate policy, and record audit evidence."""
        start_time = time.perf_counter()
        source_files = source_files or {}
        active_base_sha = base_commit_sha or patch.base_commit_sha or "unknown-base-sha"
        patch_hash = patch.content_hash
        patch_revision = patch.revision or 1

        logger.info(
            f"[SecurityGuardian] Starting security scan for run {run_id}, rev {patch_revision}, hash {patch_hash[:8]}"
        )

        all_findings: List[SecurityFindingSchema] = []
        scanners_executed: List[str] = []

        # 1. Secret and Credential Exposure Scanning
        scanners_executed.append("secret_scanner")
        secret_findings = self.secret_scanner.scan_diff(
            unified_diff=patch.unified_diff,
            run_id=run_id,
            patch_revision=patch_revision,
            patch_hash=patch_hash,
            base_commit_sha=active_base_sha,
        )
        all_findings.extend(secret_findings)

        # 2. Security Regression & Scope Inspection
        scanners_executed.append("regression_scanner")
        regression_findings = self.regression_scanner.scan_diff(
            unified_diff=patch.unified_diff,
            target_files=patch.target_files,
            run_id=run_id,
            patch_revision=patch_revision,
            patch_hash=patch_hash,
            base_commit_sha=active_base_sha,
        )
        all_findings.extend(regression_findings)

        # 3. Source Code Vulnerability Inspection on modified source files
        scanners_executed.append("ast_source_scanner")
        if self.source_scanner.bandit_available:
            scanners_executed.append("bandit_scanner")

        for file_path in patch.target_files:
            content = source_files.get(file_path, "")
            # If not in source_files, synthesize a minimal representation from diff added lines
            if not content:
                added_lines = [
                    l[1:] for l in patch.unified_diff.splitlines()
                    if l.startswith("+") and not l.startswith("+++")
                ]
                content = "\n".join(added_lines)

            source_findings = self.source_scanner.scan_code(
                file_path=file_path,
                code_content=content,
                run_id=run_id,
                patch_revision=patch_revision,
                patch_hash=patch_hash,
                base_commit_sha=active_base_sha,
            )
            all_findings.extend(source_findings)

        # 4. Dependency Vulnerability Auditing
        scanners_executed.append("dependency_auditor")
        for file_path in patch.target_files:
            clean_name = file_path.split("/")[-1].split("\\")[-1]
            if clean_name in ("pyproject.toml", "requirements.txt", "package.json"):
                dep_content = source_files.get(file_path, "")
                if not dep_content:
                    dep_content = "\n".join([
                        l[1:] for l in patch.unified_diff.splitlines()
                        if l.startswith("+") and not l.startswith("+++")
                    ])
                dep_findings = self.dependency_auditor.audit_manifest(
                    file_path=file_path,
                    content=dep_content,
                    run_id=run_id,
                    patch_revision=patch_revision,
                    patch_hash=patch_hash,
                    base_commit_sha=active_base_sha,
                )
                all_findings.extend(dep_findings)

        # 5. Policy Engine Decision
        status, can_approve, block_reasons, summary = self.policy_engine.evaluate(all_findings)
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        result = SecurityScanResult(
            run_id=run_id,
            patch_id=getattr(patch, "id", None),
            patch_revision=patch_revision,
            patch_hash=patch_hash,
            base_commit_sha=active_base_sha,
            status=status.value,
            can_approve=can_approve,
            block_reasons=block_reasons,
            findings=all_findings,
            summary=summary,
            scanners_executed=scanners_executed,
            scanners_available={
                "secret_scanner": True,
                "ast_source_scanner": True,
                "bandit": self.source_scanner.bandit_available,
                "dependency_auditor": True,
                "regression_scanner": True,
            },
            scanned_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_ms,
        )

        # 6. Database Persistence & Audit Logging
        await self._persist_scan_evidence(result=result, patch=patch, session=session)

        logger.info(
            f"[SecurityGuardian] Scan completed: status={status.value}, "
            f"findings={summary.total} (crit={summary.critical}, high={summary.high}), duration={duration_ms}ms"
        )
        return result

    async def _persist_scan_evidence(
        self,
        result: SecurityScanResult,
        patch: PatchItem,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Persist structured findings, audit record, and security events to the database."""
        async def _do_persist(db: AsyncSession):
            # Create SecurityScanRecord
            scan_record = SecurityScanRecord(
                run_id=result.run_id,
                patch_id=result.patch_id,
                patch_revision=result.patch_revision,
                patch_hash=result.patch_hash,
                base_commit_sha=result.base_commit_sha,
                status=result.status,
                findings_count=result.summary.total,
                critical_count=result.summary.critical,
                high_count=result.summary.high,
                medium_count=result.summary.medium,
                low_count=result.summary.low,
                info_count=result.summary.info,
                block_reasons=result.block_reasons,
                scanners_executed=result.scanners_executed,
                duration_ms=result.duration_ms,
            )
            db.add(scan_record)

            # Persist findings
            for f in result.findings:
                finding_model = SecurityFinding(
                    run_id=result.run_id,
                    patch_id=result.patch_id,
                    patch_revision=result.patch_revision,
                    patch_hash=result.patch_hash,
                    base_commit_sha=result.base_commit_sha,
                    category=f.category,
                    rule_id=f.rule_id,
                    title=f.title,
                    description=f.description,
                    severity=f.severity,
                    confidence=f.confidence,
                    file_path=f.file_path,
                    line_start=f.line_start,
                    line_end=f.line_end,
                    evidence_redacted=f.evidence_redacted,
                    remediation=f.remediation,
                    scanner_name=f.scanner_name,
                    scanner_version=f.scanner_version,
                    advisory_id=f.advisory_id,
                    is_blocking=f.is_blocking,
                    status=f.status,
                )
                db.add(finding_model)

            # Log agent events
            event_type = "security_gate_passed" if result.status == SecurityGateStatus.PASSED.value else "security_gate_blocked"
            message = (
                f"Security Guardian scan complete: {result.status}. "
                f"Total findings: {result.summary.total} (Crit: {result.summary.critical}, High: {result.summary.high})."
            )
            if result.block_reasons:
                message += f" Block reasons: {'; '.join(result.block_reasons[:2])}"

            audit_log = AgentLog(
                run_id=result.run_id,
                agent_name="security_guardian",
                event_type=event_type,
                message=message,
                input_summary=f"Patch rev {result.patch_revision} (hash: {result.patch_hash[:8]})",
                output_summary=f"Gate Status: {result.status} (Can Approve: {result.can_approve})",
                duration_ms=result.duration_ms,
            )
            db.add(audit_log)
            await db.commit()

        if session:
            await _do_persist(session)
        else:
            async with self.session_factory() as new_session:
                await _do_persist(new_session)

    def get_diagnostics(self) -> SecurityDiagnostics:
        """Produce system diagnostics reporting scanner availability and policy configuration."""
        scanners = [
            ScannerStatusItem(
                name="secret_scanner",
                category="credential_exposure",
                available=True,
                version=self.secret_scanner.version,
                description="Deterministic regex and entropy scanner detecting 10+ credential patterns.",
                mandatory=True,
            ),
            ScannerStatusItem(
                name="ast_source_scanner",
                category="source_vulnerability",
                available=True,
                version="1.0.0",
                description="Deterministic AST static analyzer for SQLi, command injection, path traversal, and unsafe deserialization.",
                mandatory=True,
            ),
            ScannerStatusItem(
                name="bandit",
                category="source_vulnerability",
                available=self.source_scanner.bandit_available,
                version="1.9.4" if self.source_scanner.bandit_available else None,
                description="OpenStack Bandit AST security linter for Python code.",
                mandatory=False,
            ),
            ScannerStatusItem(
                name="dependency_auditor",
                category="dependency_audit",
                available=True,
                version=self.dependency_auditor.version,
                description="Auditor for vulnerable dependencies, wildcards, and insecure plaintext package URLs.",
                mandatory=True,
            ),
            ScannerStatusItem(
                name="regression_scanner",
                category="security_regression",
                available=True,
                version=self.regression_scanner.version,
                description="Inspects diffs for deleted auth checks, disabled security filters, and scope violations.",
                mandatory=True,
            ),
        ]
        return SecurityDiagnostics(
            status="healthy",
            policy_version=self.policy_version,
            mandatory_blockers_enforced=True,
            scanners=scanners,
        )
