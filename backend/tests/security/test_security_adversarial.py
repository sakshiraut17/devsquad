"""Adversarial and Edge-Case Test Suite for AI Security Guardian Verification.

Rigorous independent verification covering:
- Test A: Approval Gate Bypass & Security Record Tampering Attempts
- Test B: Stale Evidence & Patch Mutation Invalidation
- Test C: Canary Secret Exposure & Deterministic Redaction
- Test D: Source Code AST Vulnerability Analysis (SQLi, Command Injection, eval, pickle, weak crypto)
- Test E: Security Regression & System Control Tampering
- Test F: Dependency Auditing Reality & Offline Operation Check
- Test G: Fault Injection, Scanner Failure & Fail-Closed Behavior
"""

import ast
import hashlib
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import compute_sha256
from app.db.models import (
    ApprovalRecord,
    Issue,
    Patch,
    Repository,
    Run,
    RunStatus,
    SecurityFinding,
    SecurityScanRecord,
    User,
)
from app.orchestration.nodes import security_guardian_node
from app.orchestration.routing import route_after_security
from app.orchestration.state import DevSquadState, PatchItem
from app.schemas.security import (
    SecurityCategory,
    SecurityFindingSchema,
    SecurityGateStatus,
    SecuritySeverity,
)
from app.services.security_guardian import (
    DependencyAuditor,
    PolicyEngine,
    RegressionScanner,
    SecretScanner,
    SecurityGuardianService,
    SourceCodeScanner,
)


# ==============================================================================
# TEST A: APPROVAL GATE BYPASS & TAMPERING ATTEMPTS
# ==============================================================================

@pytest.mark.asyncio
async def test_approval_fails_when_run_has_no_security_scan(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Approval must fail-closed (409 Conflict) if no security scan record exists."""
    repo = Repository(
        id="repo-adv-01",
        owner_id=default_user.id,
        github_repository_id=9801,
        full_name="devsquad/adv-01",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-adv-01",
        repository_id=repo.id,
        github_issue_number=101,
        title="Issue 01",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-adv-01",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="reviewer",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    patch_hash = compute_sha256("--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n-old\n+new\n")
    patch = Patch(
        id="patch-adv-01",
        run_id=run.id,
        revision=1,
        unified_diff="--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n-old\n+new\n",
        target_files=["f.py"],
        summary="Safe update",
        content_hash=patch_hash,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch)
    await test_db_session.commit()

    # Attempt approval without any SecurityScanRecord in DB
    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={"patch_id": patch.id, "decision": "approved", "patch_hash": patch_hash},
    )
    assert resp.status_code == 409
    assert "mandatory Security Guardian evaluation" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approval_fails_when_scan_status_is_running_or_pending(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Approval must fail-closed if security scan record status is RUNNING or PENDING."""
    repo = Repository(
        id="repo-adv-02",
        owner_id=default_user.id,
        github_repository_id=9802,
        full_name="devsquad/adv-02",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-adv-02",
        repository_id=repo.id,
        github_issue_number=102,
        title="Issue 02",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-adv-02",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="reviewer",
    )
    test_db_session.add(run)
    await test_db_session.commit()

    patch_hash = compute_sha256("diff-adv-02")
    patch = Patch(
        id="patch-adv-02",
        run_id=run.id,
        revision=1,
        unified_diff="diff-adv-02",
        target_files=["f.py"],
        summary="Update",
        content_hash=patch_hash,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch)

    # In-progress scan record
    scan_rec = SecurityScanRecord(
        id="sec-adv-02",
        run_id=run.id,
        patch_id=patch.id,
        patch_hash=patch_hash,
        status="RUNNING",
        critical_count=0,
        high_count=0,
        scanners_executed=["secret_scanner"],
        block_reasons=[],
    )
    test_db_session.add(scan_rec)
    await test_db_session.commit()

    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={"patch_id": patch.id, "decision": "approved", "patch_hash": patch_hash},
    )
    assert resp.status_code == 409
    assert "Security Guardian gate is BLOCKED" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approval_fails_when_scan_belongs_to_different_run(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """An attacker reusing a valid scan record from Run A to approve Run B must be rejected."""
    repo = Repository(
        id="repo-adv-03",
        owner_id=default_user.id,
        github_repository_id=9803,
        full_name="devsquad/adv-03",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-adv-03",
        repository_id=repo.id,
        github_issue_number=103,
        title="Issue 03",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run_target = Run(
        id="run-adv-target",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="reviewer",
    )
    test_db_session.add(run_target)

    patch_hash = compute_sha256("diff-adv-03")
    patch = Patch(
        id="patch-adv-03",
        run_id=run_target.id,
        revision=1,
        unified_diff="diff-adv-03",
        target_files=["f.py"],
        summary="Update",
        content_hash=patch_hash,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch)

    # Create a legitimate second run to satisfy foreign key constraint
    run_other = Run(
        id="run-adv-other-valid",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.PLANNING.value,
    )
    test_db_session.add(run_other)
    await test_db_session.commit()

    # Valid scan record attached to the OTHER run id
    scan_other = SecurityScanRecord(
        id="sec-adv-other",
        run_id=run_other.id,
        patch_id=None,
        patch_hash=patch_hash,
        status="PASSED",
        critical_count=0,
        high_count=0,
        scanners_executed=["secret_scanner"],
        block_reasons=[],
    )
    test_db_session.add(scan_other)
    await test_db_session.commit()

    resp = await async_client.post(
        f"/api/v1/runs/{run_target.id}/approve",
        json={"patch_id": patch.id, "decision": "approved", "patch_hash": patch_hash},
    )
    assert resp.status_code == 409
    assert "mandatory Security Guardian evaluation" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approval_fails_when_scan_status_is_passed_but_has_critical_findings(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Tamper resistance: If the DB record claims status=PASSED but critical_count > 0, approve must reject."""
    repo = Repository(
        id="repo-adv-04",
        owner_id=default_user.id,
        github_repository_id=9804,
        full_name="devsquad/adv-04",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-adv-04",
        repository_id=repo.id,
        github_issue_number=104,
        title="Issue 04",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-adv-04",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="reviewer",
    )
    test_db_session.add(run)

    patch_hash = compute_sha256("diff-adv-04")
    patch = Patch(
        id="patch-adv-04",
        run_id=run.id,
        revision=1,
        unified_diff="diff-adv-04",
        target_files=["f.py"],
        summary="Update",
        content_hash=patch_hash,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch)

    # Forged scan record claiming status="PASSED" but critical_count=1
    tampered_scan = SecurityScanRecord(
        id="sec-adv-tampered",
        run_id=run.id,
        patch_id=patch.id,
        patch_hash=patch_hash,
        status="PASSED",
        critical_count=1,
        high_count=0,
        scanners_executed=["secret_scanner"],
        block_reasons=["Forged record test"],
    )
    test_db_session.add(tampered_scan)
    await test_db_session.commit()

    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={"patch_id": patch.id, "decision": "approved", "patch_hash": patch_hash},
    )
    assert resp.status_code == 409
    assert "Security Guardian gate is BLOCKED" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approval_fails_when_active_blocking_finding_present(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Tamper resistance: If an active blocking finding exists in SecurityFinding, approve must reject."""
    repo = Repository(
        id="repo-adv-05",
        owner_id=default_user.id,
        github_repository_id=9805,
        full_name="devsquad/adv-05",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-adv-05",
        repository_id=repo.id,
        github_issue_number=105,
        title="Issue 05",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-adv-05",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="reviewer",
    )
    test_db_session.add(run)

    patch_hash = compute_sha256("diff-adv-05")
    patch = Patch(
        id="patch-adv-05",
        run_id=run.id,
        revision=1,
        unified_diff="diff-adv-05",
        target_files=["f.py"],
        summary="Update",
        content_hash=patch_hash,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch)

    # Clean scan record
    scan_rec = SecurityScanRecord(
        id="sec-adv-05",
        run_id=run.id,
        patch_id=patch.id,
        patch_hash=patch_hash,
        status="PASSED",
        critical_count=0,
        high_count=0,
        scanners_executed=["secret_scanner"],
        block_reasons=[],
    )
    test_db_session.add(scan_rec)

    # But an active blocking finding remains in SecurityFinding table
    active_finding = SecurityFinding(
        run_id=run.id,
        patch_id=patch.id,
        patch_revision=1,
        patch_hash=patch_hash,
        category="credential_exposure",
        rule_id="SEC-001",
        title="Active Secret Finding",
        description="Blocking finding",
        severity="CRITICAL",
        confidence="HIGH",
        scanner_name="secret_scanner",
        scanner_version="1.0.0",
        is_blocking=True,
        status="ACTIVE",
    )
    test_db_session.add(active_finding)
    await test_db_session.commit()

    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={"patch_id": patch.id, "decision": "approved", "patch_hash": patch_hash},
    )
    assert resp.status_code == 409
    assert "Security Guardian gate is BLOCKED" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approval_succeeds_when_all_security_controls_satisfied(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Legitimate workflow: pristine scan + zero blockers + matching hash -> Approved with audit log."""
    repo = Repository(
        id="repo-adv-06",
        owner_id=default_user.id,
        github_repository_id=9806,
        full_name="devsquad/adv-06",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-adv-06",
        repository_id=repo.id,
        github_issue_number=106,
        title="Issue 06",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-adv-06",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="reviewer",
    )
    test_db_session.add(run)

    patch_hash = compute_sha256("diff-adv-06-pristine")
    patch = Patch(
        id="patch-adv-06",
        run_id=run.id,
        revision=1,
        unified_diff="diff-adv-06-pristine",
        target_files=["f.py"],
        summary="Clean safe patch",
        content_hash=patch_hash,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch)

    scan_rec = SecurityScanRecord(
        id="sec-adv-06",
        run_id=run.id,
        patch_id=patch.id,
        patch_hash=patch_hash,
        status="PASSED",
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        info_count=0,
        scanners_executed=["secret_scanner", "ast_source_scanner", "dependency_auditor"],
        block_reasons=[],
    )
    test_db_session.add(scan_rec)
    await test_db_session.commit()

    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={
            "patch_id": patch.id,
            "decision": "approved",
            "patch_hash": patch_hash,
            "feedback": "LGTM. Verified by Security Guardian.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "approved"
    assert data["approver_id"] == default_user.id
    assert data["patch_hash"] == patch_hash

    # Verify run status is now APPROVED
    await test_db_session.refresh(run)
    assert run.status == RunStatus.APPROVED.value


# ==============================================================================
# TEST B: STALE EVIDENCE & PATCH MUTATION
# ==============================================================================

@pytest.mark.asyncio
async def test_patch_mutation_invalidates_prior_scan(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """If a patch's content is modified after scanning, the old scan record is invalid."""
    repo = Repository(
        id="repo-adv-stale",
        owner_id=default_user.id,
        github_repository_id=9807,
        full_name="devsquad/adv-stale",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-adv-stale",
        repository_id=repo.id,
        github_issue_number=107,
        title="Issue Stale",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-adv-stale",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="reviewer",
    )
    test_db_session.add(run)

    initial_diff = "diff-initial"
    initial_hash = compute_sha256(initial_diff)

    # Patch was updated with mutated content
    mutated_diff = "diff-mutated-with-unscanned-code"
    mutated_hash = compute_sha256(mutated_diff)

    patch = Patch(
        id="patch-adv-stale",
        run_id=run.id,
        revision=1,
        unified_diff=mutated_diff,
        target_files=["f.py"],
        summary="Mutated",
        content_hash=mutated_hash,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch)

    # Scan record only exists for initial_hash
    scan_initial = SecurityScanRecord(
        id="sec-adv-stale",
        run_id=run.id,
        patch_id=patch.id,
        patch_hash=initial_hash,
        status="PASSED",
        critical_count=0,
        high_count=0,
        scanners_executed=["secret_scanner"],
        block_reasons=[],
    )
    test_db_session.add(scan_initial)
    await test_db_session.commit()

    # Approving with current patch's mutated_hash -> fails because scan only exists for initial_hash
    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={"patch_id": patch.id, "decision": "approved", "patch_hash": mutated_hash},
    )
    assert resp.status_code == 409
    assert "mandatory Security Guardian evaluation" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approval_rejects_superseded_older_patch_revision(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """Attempting to approve revision 1 when revision 2 exists must be rejected."""
    repo = Repository(
        id="repo-adv-super",
        owner_id=default_user.id,
        github_repository_id=9808,
        full_name="devsquad/adv-super",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-adv-super",
        repository_id=repo.id,
        github_issue_number=108,
        title="Issue Super",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-adv-super",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
        current_node="reviewer",
    )
    test_db_session.add(run)

    hash1 = compute_sha256("diff-rev-1")
    patch1 = Patch(
        id="patch-rev-1",
        run_id=run.id,
        revision=1,
        unified_diff="diff-rev-1",
        target_files=["f.py"],
        summary="Revision 1",
        content_hash=hash1,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch1)

    hash2 = compute_sha256("diff-rev-2")
    patch2 = Patch(
        id="patch-rev-2",
        run_id=run.id,
        revision=2,
        unified_diff="diff-rev-2",
        target_files=["f.py"],
        summary="Revision 2 (Latest)",
        content_hash=hash2,
        validation_status="VALIDATED",
    )
    test_db_session.add(patch2)
    await test_db_session.commit()

    resp = await async_client.post(
        f"/api/v1/runs/{run.id}/approve",
        json={"patch_id": patch1.id, "decision": "approved", "patch_hash": hash1},
    )
    assert resp.status_code == 409
    assert "superseded by newer revision 2" in resp.json()["detail"]


# ==============================================================================
# TEST C: CANARY SECRET EXPOSURE & DETERMINISTIC REDACTION
# ==============================================================================

def test_canary_secrets_detected_and_redacted_consistently():
    """Verify high-entropy synthetic canary credentials are flagged and NEVER stored in plaintext."""
    scanner = SecretScanner()

    canaries = [
        ("AWS Key", "AKIA1234567890ABCDEF"),
        ("GitHub PAT", "ghp_" + "CANARYTESTTOKEN1234567890abcdef123456"),
        ("OpenAI Key", "sk-proj-" + "CANARYTESTKEY1234567890abcdefghijklmnopqrstuvwxyz1234"),
        ("Slack Bot Token", "xoxb" + "-123456789012-" + "3456789012345-" + "canarytokenstring99"),
        ("RSA Key Header", "-----BEGIN RSA PRIVATE KEY-----"),
    ]

    for label, secret_canary in canaries:
        diff = f"""--- a/secret.py
+++ b/secret.py
@@ -1 +1,2 @@
 def creds():
+    token = "{secret_canary}"
"""
        findings = scanner.scan_diff(
            diff, run_id="canary-run", patch_revision=1, patch_hash="canary-hash"
        )
        assert len(findings) >= 1, f"Failed to detect {label}"
        f = findings[0]
        assert f.severity == SecuritySeverity.CRITICAL.value
        assert f.is_blocking is True

        # Crucial anti-leak invariant:
        # 1. Raw canary MUST NOT appear in description
        assert secret_canary not in f.description
        # 2. Raw canary MUST NOT appear in evidence_redacted (unless it's the PEM header itself, but full key body is redacted)
        if not secret_canary.startswith("-----"):
            assert secret_canary not in (f.evidence_redacted or "")
            assert "[REDACTED_SECRET:" in (f.evidence_redacted or "")


def test_benign_placeholders_do_not_trigger_false_positives():
    """Benign placeholder strings in code should not be flagged as critical secrets."""
    scanner = SecretScanner()
    benign_diff = """--- a/config.py
+++ b/config.py
@@ -1,3 +1,3 @@
-API_KEY = None
+API_KEY = "YOUR_API_KEY_HERE"
+SECRET = "placeholder-secret"
+DUMMY = "<INSERT_KEY_HERE>"
"""
    findings = scanner.scan_diff(
        benign_diff, run_id="benign-run", patch_revision=1, patch_hash="benign-hash"
    )
    assert len(findings) == 0


@pytest.mark.asyncio
async def test_canary_secret_not_leaked_in_api_response(
    test_db_session: AsyncSession,
    async_client: AsyncClient,
    default_user: User,
):
    """GET /api/v1/runs/{id}/security must never expose raw canary secrets in JSON response."""
    repo = Repository(
        id="repo-canary-api",
        owner_id=default_user.id,
        github_repository_id=9809,
        full_name="devsquad/canary-api",
        default_branch="main",
    )
    test_db_session.add(repo)
    await test_db_session.commit()

    issue = Issue(
        id="issue-canary-api",
        repository_id=repo.id,
        github_issue_number=109,
        title="Canary API Issue",
        state="open",
    )
    test_db_session.add(issue)
    await test_db_session.commit()

    run = Run(
        id="run-canary-api",
        repository_id=repo.id,
        issue_id=issue.id,
        status=RunStatus.AWAITING_APPROVAL.value,
    )
    test_db_session.add(run)

    raw_canary = "ghp_" + "SUPERSECRETLEAKTOKEN9999999999999999"
    diff = f"""--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n+KEY = "{raw_canary}"\n"""
    patch_item = PatchItem(
        unified_diff=diff,
        target_files=["app.py"],
        content_hash=compute_sha256(diff),
        revision=1,
        base_commit_sha="canarysha",
        summary="Add key",
    )

    service = SecurityGuardianService()
    await service.scan_patch(patch=patch_item, run_id=run.id, session=test_db_session)

    resp = await async_client.get(f"/api/v1/runs/{run.id}/security")
    assert resp.status_code == 200
    resp_text = resp.text

    # The raw secret MUST NOT appear anywhere in the JSON response text
    assert raw_canary not in resp_text
    assert "[REDACTED_SECRET:" in resp_text


# ==============================================================================
# TEST D: SOURCE CODE AST VULNERABILITY ANALYSIS
# ==============================================================================

def test_ast_detects_sqli_in_all_concatenation_forms():
    """Verify AST visitor detects SQLi via f-string, % operator, and + string concat."""
    scanner = SourceCodeScanner()

    # Form 1: f-string
    code1 = """def q1(db, uid):
    return db.execute(f"SELECT * FROM users WHERE id = '{uid}'")
"""
    f1 = scanner.scan_code("q1.py", code1, "r", 1, "h")
    assert any("SQL" in f.title and f.severity == SecuritySeverity.CRITICAL.value for f in f1)

    # Form 2: % string formatting
    code2 = """def q2(db, uid):
    return db.execute("SELECT * FROM users WHERE id = '%s'" % uid)
"""
    f2 = scanner.scan_code("q2.py", code2, "r", 1, "h")
    assert any("SQL" in f.title and f.severity == SecuritySeverity.CRITICAL.value for f in f2)

    # Form 3: + concatenation
    code3 = """def q3(db, uid):
    return db.execute("SELECT * FROM users WHERE id = '" + uid + "'")
"""
    f3 = scanner.scan_code("q3.py", code3, "r", 1, "h")
    assert any("SQL" in f.title and f.severity == SecuritySeverity.CRITICAL.value for f in f3)


def test_ast_detects_command_injection_and_os_system():
    """Verify AST visitor flags subprocess with shell=True and os.system."""
    scanner = SourceCodeScanner()

    code1 = """import subprocess
def run_tool(user_input):
    subprocess.run(f"echo {user_input}", shell=True)
"""
    f1 = scanner.scan_code("tool.py", code1, "r", 1, "h")
    assert any("Command" in f.title and f.severity == SecuritySeverity.CRITICAL.value for f in f1)

    code2 = """import os
def delete_dir(user_path):
    os.system("rm -rf " + user_path)
"""
    f2 = scanner.scan_code("del.py", code2, "r", 1, "h")
    assert any("Dangerous Shell Execution" in f.title for f in f2)


def test_ast_detects_eval_exec_and_pickle_deserialization():
    """Verify AST visitor flags dynamic code execution and insecure pickle."""
    scanner = SourceCodeScanner()

    code_eval = """def eval_code(user_str):
    return eval(user_str)
"""
    f_eval = scanner.scan_code("eval.py", code_eval, "r", 1, "h")
    assert any("Dynamic Code Execution" in f.title for f in f_eval)

    code_pickle = """import pickle
def load_data(raw_bytes):
    return pickle.loads(raw_bytes)
"""
    f_pickle = scanner.scan_code("pickle.py", code_pickle, "r", 1, "h")
    assert any("Deserialization" in f.title and f.severity == SecuritySeverity.CRITICAL.value for f in f_pickle)


def test_ast_detects_weak_crypto_hashes():
    """Verify AST visitor flags hashlib.md5 and hashlib.sha1 unless usedforsecurity=False."""
    scanner = SourceCodeScanner()

    weak_code = """import hashlib
def make_hash(data):
    return hashlib.md5(data).hexdigest()
"""
    findings = scanner.scan_code("hash.py", weak_code, "r", 1, "h")
    assert any("Weak Cryptographic Hash" in f.title for f in findings)

    # Safe override with usedforsecurity=False should NOT be flagged
    safe_code = """import hashlib
def safe_checksum(data):
    return hashlib.md5(data, usedforsecurity=False).hexdigest()
"""
    safe_findings = scanner.scan_code("safe_hash.py", safe_code, "r", 1, "h")
    assert not any("Weak Cryptographic Hash" in f.title for f in safe_findings)


def test_ast_scanner_handles_syntax_errors_gracefully():
    """AST scanner should not crash on malformed Python syntax."""
    scanner = SourceCodeScanner()
    broken_code = """def broken(:
    return 1 +
"""
    # Should not raise exception
    findings = scanner.scan_code("broken.py", broken_code, "r", 1, "h")
    assert isinstance(findings, list)


# ==============================================================================
# TEST E: SECURITY REGRESSION & TAMPER SCANNER
# ==============================================================================

def test_regression_scanner_flags_removal_of_security_controls():
    """Detects removal of Depends(get_current_user) or verify_stream_ticket."""
    scanner = RegressionScanner()

    # Case 1: Removing auth dependency
    diff_auth = """--- a/api.py
+++ b/api.py
@@ -10,3 +10,3 @@
-@router.get("/admin", dependencies=[Depends(get_current_user)])
+@router.get("/admin")
 def admin():
     pass
"""
    findings1 = scanner.scan_diff(diff_auth, ["api.py"], "r", 1, "h")
    assert any("Security Control Regression" in f.title for f in findings1)

    # Case 2: Removing verify_stream_ticket
    diff_stream = """--- a/stream.py
+++ b/stream.py
@@ -5,3 +5,3 @@
-ticket = verify_stream_ticket(token)
+ticket = None
"""
    findings2 = scanner.scan_diff(diff_stream, ["stream.py"], "r", 1, "h")
    assert any("Security Control Regression" in f.title for f in findings2)


def test_regression_scanner_flags_prohibited_system_files():
    """Detects modifications to .env, alembic.ini, or devsquad.db."""
    scanner = RegressionScanner()

    diff_env = """--- a/.env
+++ b/.env
@@ -1 +1 @@
-SECRET=1
+SECRET=2
"""
    findings = scanner.scan_diff(diff_env, [".env"], "r", 1, "h")
    assert any("Prohibited System" in f.title for f in findings)


# ==============================================================================
# TEST F: DEPENDENCY AUDITING REALITY & OFFLINE DETERMINISM
# ==============================================================================

def test_dependency_auditor_detects_known_vulnerable_packages():
    """Detects pycrypto, pickle5, telnetlib in requirements.txt."""
    auditor = DependencyAuditor()
    reqs = """cryptography==42.0.0
pycrypto==2.6.1
pickle5==0.0.12
telnetlib3==2.0.4
"""
    findings = auditor.audit_manifest("requirements.txt", reqs, "r", 1, "h")
    titles = [f.title for f in findings]
    assert any("pycrypto" in t.lower() for t in titles)
    assert any("pickle5" in t.lower() for t in titles)


def test_dependency_auditor_flags_plaintext_http_repository():
    """Detects unencrypted HTTP package repositories."""
    auditor = DependencyAuditor()
    reqs = "--index-url http://insecure-pypi.internal/simple/\nfastapi==0.115.0\n"
    findings = auditor.audit_manifest("requirements.txt", reqs, "r", 1, "h")
    assert any("Plaintext Package Repository" in f.title for f in findings)


def test_dependency_auditor_flags_wildcard_dependencies():
    """Detects unbounded wildcard dependencies in requirements.txt and package.json."""
    auditor = DependencyAuditor()

    # Python wildcard
    findings_py = auditor.audit_manifest("requirements.txt", "requests=*\n", "r", 1, "h")
    assert any("Wildcard Dependency" in f.title for f in findings_py)

    # Node package.json wildcard
    pkg_json = '{"dependencies": {"express": "*", "lodash": "^4.17.21"}}'
    findings_node = auditor.audit_manifest("package.json", pkg_json, "r", 1, "h")
    assert any("Wildcard Node Dependency (express)" in f.title for f in findings_node)


def test_dependency_auditor_operates_completely_offline():
    """Verify DependencyAuditor does not make socket/network connections."""
    import socket

    # Save original socket
    orig_connect = socket.socket.connect

    def fake_connect(*args, **kwargs):
        raise RuntimeError("Network access attempted during offline dependency audit!")

    socket.socket.connect = fake_connect
    try:
        auditor = DependencyAuditor()
        findings = auditor.audit_manifest(
            "requirements.txt", "pycrypto==2.6.1\nrequests==2.31.0\n", "r", 1, "h"
        )
        assert len(findings) >= 1
    finally:
        socket.socket.connect = orig_connect


# ==============================================================================
# TEST G: FAULT INJECTION, SCANNER FAILURE & FAIL-CLOSED BEHAVIOR
# ==============================================================================

@pytest.mark.asyncio
async def test_security_guardian_node_fails_closed_when_patch_missing():
    """If state lacks current_patch, security_guardian_node fails closed."""
    state = DevSquadState(
        run_id="run-missing-patch",
        repository_id="repo-1",
        issue_id="issue-1",
        current_patch=None,
    )
    result = await security_guardian_node(state)
    assert result["status"] == "FAILED"
    assert result["error_code"] == "SECURITY_SCAN_FAILED"


def test_route_after_security_routing_logic():
    """Verify route_after_security routes to tester on PASSED, repair on BLOCKED, and finalize on max retries."""
    # 1. Clean pass
    clean_state = DevSquadState(
        run_id="r1",
        repository_id="repo-1",
        issue_id="issue-1",
        security_result={"status": "PASSED", "can_approve": True},
    )
    assert route_after_security(clean_state) == "sandbox_tester_node"

    # 2. Blocked with repair attempts available -> coder_node
    blocked_state_repairable = DevSquadState(
        run_id="r2",
        repository_id="repo-1",
        issue_id="issue-1",
        repair_attempts=0,
        max_repair_attempts=3,
        security_result={"status": "BLOCKED", "can_approve": False},
    )
    assert route_after_security(blocked_state_repairable) == "coder_node"

    # 3. Blocked with repair attempts exhausted -> finalization_node
    blocked_state_exhausted = DevSquadState(
        run_id="r3",
        repository_id="repo-1",
        issue_id="issue-1",
        repair_attempts=3,
        max_repair_attempts=3,
        security_result={"status": "BLOCKED", "can_approve": False},
    )
    assert route_after_security(blocked_state_exhausted) == "finalization_node"
