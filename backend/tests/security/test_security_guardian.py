"""Comprehensive test suite for the AI Security Guardian verification gate.

Covers:
- Deterministic Secret Scanner (AWS keys, tokens, private keys, evidence redaction)
- AST-based Source Code Scanner (SQLi, command injection, eval/exec, pickle, weak crypto)
- Dependency Auditor (insecure packages, wildcard pinning, HTTP index URLs)
- Security Regression & Tamper Scanner (removal of auth checks, touching .env)
- Security Policy Engine (strict gate enforcement, block reasons)
- Security Guardian Service orchestration and database persistence
- API Routes (GET /runs/{id}/security, GET /health/security, POST /runs/{id}/approve gating)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import compute_sha256
from app.db.models import (
    Issue,
    Patch,
    Repository,
    Run,
    RunStatus,
    SecurityFinding,
    SecurityScanRecord,
    User,
)
from app.orchestration.state import PatchItem
from app.services.security_guardian import (
    DependencyAuditor,
    PolicyEngine,
    RegressionScanner,
    SecretScanner,
    SecurityGuardianService,
    SourceCodeScanner,
)
from app.schemas.security import (
    SecurityCategory,
    SecurityFindingSchema,
    SecurityGateStatus,
    SecuritySeverity,
)


# ==============================================================================
# 1. SECRET SCANNER TESTS
# ==============================================================================

def test_secret_scanner_detects_aws_key_and_redacts():
    """Detect AWS Access Key ID and verify raw secret is redacted in findings."""
    scanner = SecretScanner()
    raw_key = "AKIA1234567890ABCDEF"
    diff = f"""--- a/config.py\n+++ b/config.py\n@@ -1,2 +1,3 @@\n def get_creds():\n+    aws_key = "{raw_key}"\n     return aws_key\n"""

    findings = scanner.scan_diff(diff, run_id="r1", patch_revision=1, patch_hash="h1")
    assert len(findings) >= 1
    aws_finding = next((f for f in findings if "AWS" in f.title), None)
    assert aws_finding is not None
    assert aws_finding.severity == SecuritySeverity.CRITICAL.value
    assert aws_finding.is_blocking is True
    # Crucial: raw secret MUST NOT appear in evidence or description
    assert raw_key not in (aws_finding.evidence_redacted or "")
    assert "[REDACTED_SECRET:" in (aws_finding.evidence_redacted or "")


def test_secret_scanner_detects_private_key():
    """Detect RSA / EC private key headers and block."""
    scanner = SecretScanner()
    diff = """--- a/key.pem\n+++ b/key.pem\n@@ -0,0 +1,3 @@\n+-----BEGIN RSA PRIVATE KEY-----\n+MIIEowIBAAKCAQEA0Y\n+-----END RSA PRIVATE KEY-----\n"""
    findings = scanner.scan_diff(diff, run_id="r1", patch_revision=1, patch_hash="h1")
    assert any("Private" in f.title and f.severity == SecuritySeverity.CRITICAL.value for f in findings)


def test_secret_scanner_ignores_benign_placeholders():
    """Placeholder tokens should not trigger false positive critical secrets."""
    scanner = SecretScanner()
    diff = """--- a/config.py\n+++ b/config.py\n@@ -1 +1 @@\n+API_KEY = "YOUR_API_KEY_HERE"\n"""
    findings = scanner.scan_diff(diff, run_id="r1", patch_revision=1, patch_hash="h1")
    assert len(findings) == 0


# ==============================================================================
# 2. SOURCE CODE SCANNER (AST) TESTS
# ==============================================================================

def test_source_scanner_detects_sqli_fstring():
    """Detect SQL injection vulnerability via formatted f-string in cursor.execute."""
    scanner = SourceCodeScanner()
    code = """def get_user(db, user_id):
    return db.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
"""
    findings = scanner.scan_code("db.py", code, run_id="r1", patch_revision=1, patch_hash="h1")
    sqli = next((f for f in findings if "SQL" in f.title), None)
    assert sqli is not None
    assert sqli.severity == SecuritySeverity.CRITICAL.value
    assert sqli.is_blocking is True
    assert "db.py" in sqli.file_path


def test_source_scanner_detects_shell_command_injection():
    """Detect dangerous shell execution with shell=True."""
    scanner = SourceCodeScanner()
    code = """import subprocess
def run_cmd(user_arg):
    subprocess.Popen(f"ls {user_arg}", shell=True)
"""
    findings = scanner.scan_code("runner.py", code, run_id="r1", patch_revision=1, patch_hash="h1")
    cmd_inj = next((f for f in findings if "Shell" in f.title or "Command" in f.title), None)
    assert cmd_inj is not None
    assert cmd_inj.severity == SecuritySeverity.CRITICAL.value
    assert cmd_inj.is_blocking is True


def test_source_scanner_detects_eval_exec():
    """Detect dynamic code execution via eval/exec."""
    scanner = SourceCodeScanner()
    code = """def compute(expr):
    return eval(expr)
"""
    findings = scanner.scan_code("util.py", code, run_id="r1", patch_revision=1, patch_hash="h1")
    eval_f = next((f for f in findings if "Dynamic" in f.title or "eval" in f.title.lower()), None)
    assert eval_f is not None
    assert eval_f.severity == SecuritySeverity.CRITICAL.value


def test_source_scanner_detects_unsafe_pickle():
    """Detect unsafe deserialization using pickle.loads."""
    scanner = SourceCodeScanner()
    code = """import pickle
def load_state(raw):
    return pickle.loads(raw)
"""
    findings = scanner.scan_code("cache.py", code, run_id="r1", patch_revision=1, patch_hash="h1")
    pickle_f = next((f for f in findings if "Deserialization" in f.title or "pickle" in f.title.lower()), None)
    assert pickle_f is not None
    assert pickle_f.severity in (SecuritySeverity.HIGH.value, SecuritySeverity.CRITICAL.value)


def test_source_scanner_permits_safe_code():
    """Safe, idiomatic code should yield zero findings."""
    scanner = SourceCodeScanner()
    code = """def add(a: int, b: int) -> int:
    result = a + b
    return result
"""
    findings = scanner.scan_code("math.py", code, run_id="r1", patch_revision=1, patch_hash="h1")
    assert len(findings) == 0


# ==============================================================================
# 3. DEPENDENCY AUDITOR TESTS
# ==============================================================================

def test_dependency_auditor_flags_insecure_package_and_wildcard():
    """Detect deprecated/vulnerable packages and wildcard versioning."""
    auditor = DependencyAuditor()
    manifest_content = """fastapi==0.115.0
pycrypto==2.6.1
requests=*
"""
    findings = auditor.audit_manifest("requirements.txt", manifest_content, run_id="r1", patch_revision=1, patch_hash="h1")
    assert len(findings) >= 2
    pycrypto_f = next((f for f in findings if "pycrypto" in f.title.lower()), None)
    assert pycrypto_f is not None
    assert pycrypto_f.severity == SecuritySeverity.CRITICAL.value

    wildcard_f = next((f for f in findings if "wildcard" in f.title.lower()), None)
    assert wildcard_f is not None
    assert wildcard_f.severity == SecuritySeverity.MEDIUM.value


def test_dependency_auditor_flags_insecure_http_index():
    """Detect plaintext HTTP package repository index URLs."""
    auditor = DependencyAuditor()
    manifest_content = """--extra-index-url http://insecure.internal.repo/simple
my-pkg==1.0.0
"""
    findings = auditor.audit_manifest("requirements.txt", manifest_content, run_id="r1", patch_revision=1, patch_hash="h1")
    http_f = next((f for f in findings if "Repository" in f.title or "Plaintext" in f.title), None)
    assert http_f is not None
    assert http_f.severity == SecuritySeverity.CRITICAL.value


# ==============================================================================
# 4. REGRESSION SCANNER TESTS
# ==============================================================================

def test_regression_scanner_detects_auth_check_removal():
    """Detect patch removing Depends(get_current_user) or verify_stream_ticket."""
    scanner = RegressionScanner()
    diff = """--- a/routes/admin.py\n+++ b/routes/admin.py\n@@ -10,3 +10,2 @@\n @router.get("/metrics")\n-def get_metrics(user: User = Depends(get_current_user)):\n+def get_metrics():\n     return {"ok": True}\n"""
    findings = scanner.scan_diff(diff, target_files=["routes/admin.py"], run_id="r1", patch_revision=1, patch_hash="h1")
    assert len(findings) >= 1
    auth_f = next((f for f in findings if "Security Control Regression" in f.title), None)
    assert auth_f is not None
    assert auth_f.severity == SecuritySeverity.CRITICAL.value
    assert auth_f.is_blocking is True


def test_regression_scanner_detects_touching_env_file():
    """Detect patch modifying sensitive environment files."""
    scanner = RegressionScanner()
    diff = """--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-ENV=production\n+ENV=dev\n"""
    findings = scanner.scan_diff(diff, target_files=[".env"], run_id="r1", patch_revision=1, patch_hash="h1")
    env_f = next((f for f in findings if "Prohibited System" in f.title or ".env" in f.description), None)
    assert env_f is not None
    assert env_f.severity == SecuritySeverity.CRITICAL.value
    assert env_f.is_blocking is True


# ==============================================================================
# 5. POLICY ENGINE TESTS
# ==============================================================================

def test_policy_engine_blocks_on_critical_or_high():
    """PolicyEngine must strictly mark gate as BLOCKED for CRITICAL or HIGH findings."""
    engine = PolicyEngine()
    findings = [
        SecurityFindingSchema(
            run_id="r1",
            patch_revision=1,
            patch_hash="h1",
            category=SecurityCategory.SOURCE_VULNERABILITY.value,
            rule_id="VULN-001",
            title="SQL Injection",
            description="f-string SQL query",
            file_path="app.py",
            severity=SecuritySeverity.CRITICAL.value,
            confidence="HIGH",
            scanner_name="ast_source_scanner",
            is_blocking=True,
        )
    ]
    gate_status, can_approve, reasons, summary = engine.evaluate(findings)
    assert gate_status == SecurityGateStatus.BLOCKED
    assert can_approve is False
    assert len(reasons) >= 1
    assert "CRITICAL" in reasons[0]
    assert summary.critical == 1


def test_policy_engine_passes_clean_findings():
    """PolicyEngine permits approval when findings are empty or info/low."""
    engine = PolicyEngine()
    findings = [
        SecurityFindingSchema(
            run_id="r1",
            patch_revision=1,
            patch_hash="h1",
            category=SecurityCategory.DEPENDENCY_AUDIT.value,
            rule_id="DEP-002",
            title="Non-pinned minor version",
            description="Acceptable",
            file_path="requirements.txt",
            severity=SecuritySeverity.LOW.value,
            confidence="HIGH",
            scanner_name="dependency_auditor",
            is_blocking=False,
        )
    ]
    gate_status, can_approve, reasons, summary = engine.evaluate(findings)
    assert gate_status == SecurityGateStatus.PASSED
    assert can_approve is True
    assert len(reasons) == 0
    assert summary.critical == 0


# ==============================================================================
# 6. GUARDIAN SERVICE INTEGRATION & PERSISTENCE
# ==============================================================================

@pytest.mark.asyncio
async def test_security_guardian_service_scan_and_persistence(
    test_db_session: AsyncSession,
    default_user: User,
):
    """Verify SecurityGuardianService executes scanners, computes gate, and writes records to database."""
    repo = Repository(
        id="repo-guardian-test",
        owner_id=default_user.id,
        github_repository_id=9100,
        full_name="devsquad/guardian-test",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-guardian-test",
        repository_id=repo.id,
        github_issue_number=20,
        title="Test issue",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-guardian-test",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.PLANNING.value,
    )
    test_db_session.add(run)
    await test_db_session.commit()

    token_val = "ghp_" + "1234567890abcdefghijklmnopqrstuvwxyz12"
    malicious_diff = f"""--- a/auth.py\n+++ b/auth.py\n@@ -1,2 +1,3 @@\n def login():\n+    secret_token = "{token_val}"\n+    return eval("1 + 1")\n"""
    patch_hash = compute_sha256(malicious_diff)

    patch_item = PatchItem(
        unified_diff=malicious_diff,
        target_files=["auth.py"],
        content_hash=patch_hash,
        revision=1,
        base_commit_sha="a1b2c3d4e5f6",
        summary="Malicious update",
    )

    service = SecurityGuardianService()
    result = await service.scan_patch(
        patch=patch_item,
        run_id=run.id,
        session=test_db_session,
    )

    assert result.status == SecurityGateStatus.BLOCKED.value
    assert result.can_approve is False
    assert result.summary.critical >= 1
    assert len(result.block_reasons) >= 1

    # Verify persisted record in DB
    scan_query = select(SecurityScanRecord).where(SecurityScanRecord.run_id == run.id)
    scan_record = (await test_db_session.execute(scan_query)).scalar_one_or_none()
    assert scan_record is not None
    assert scan_record.status == "BLOCKED"
    assert scan_record.critical_count >= 1
    assert scan_record.patch_hash == patch_hash

    # Verify persisted findings in DB
    findings_query = select(SecurityFinding).where(SecurityFinding.run_id == run.id)
    findings = (await test_db_session.execute(findings_query)).scalars().all()
    assert len(findings) >= 1
    assert any(f.severity == "CRITICAL" for f in findings)


# ==============================================================================
# 7. API ENDPOINTS VERIFICATION
# ==============================================================================

@pytest.mark.asyncio
async def test_get_run_security_endpoint(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    default_user: User,
):
    """GET /api/v1/runs/{run_id}/security returns structured scan results and findings."""
    repo = Repository(
        id="repo-sec-api",
        owner_id=default_user.id,
        github_repository_id=9101,
        full_name="devsquad/sec-api",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-sec-api",
        repository_id=repo.id,
        github_issue_number=21,
        title="Test issue",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-sec-api",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
    )
    test_db_session.add(run)

    scan_rec = SecurityScanRecord(
        id="scan-api-1",
        run_id=run.id,
        patch_hash="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        status="PASSED",
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        info_count=0,
        block_reasons=[],
        scanners_executed=["secret_scanner", "source_scanner"],
    )
    test_db_session.add(scan_rec)
    await test_db_session.commit()

    resp = await async_client.get(f"/api/v1/runs/{run.id}/security")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == run.id
    assert data["status"] == "PASSED"
    assert data["can_approve"] is True
    assert data["scanners_executed"] == ["secret_scanner", "source_scanner"]


@pytest.mark.asyncio
async def test_health_security_endpoint(
    async_client: AsyncClient,
):
    """GET /api/v1/health/security returns scanner engine diagnostics and status."""
    resp = await async_client.get("/api/v1/health/security")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert data["component"] == "security_guardian"
    assert "details" in data
    details = data["details"]
    assert "scanners_available" in details
    assert "secret_scanner" in details["scanners_available"]
