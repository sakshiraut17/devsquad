"""Pydantic schemas for AI Security Guardian findings, scan results, and diagnostics."""

from datetime import datetime, timezone
import enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SecuritySeverity(str, enum.Enum):
    """Normalized security finding severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class SecurityCategory(str, enum.Enum):
    """Categorization for detected security risks."""
    SECRET_EXPOSURE = "secret_exposure"
    SOURCE_VULNERABILITY = "source_vulnerability"
    DEPENDENCY_AUDIT = "dependency_audit"
    SECURITY_REGRESSION = "security_regression"
    PATCH_SCOPE = "patch_scope"


class SecurityGateStatus(str, enum.Enum):
    """Gate decision outcome for human approval eligibility."""
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"
    UNVERIFIED = "UNVERIFIED"
    SCANNING = "SCANNING"


class SecurityFindingSchema(BaseModel):
    """Structured security finding discovered by the Security Guardian."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    run_id: str
    patch_id: Optional[str] = None
    patch_revision: int = 1
    patch_hash: str
    base_commit_sha: Optional[str] = None
    category: str
    rule_id: str
    title: str
    description: str
    severity: str
    confidence: str = "HIGH"
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    evidence_redacted: Optional[str] = None
    remediation: Optional[str] = None
    scanner_name: str
    scanner_version: Optional[str] = None
    advisory_id: Optional[str] = None
    is_blocking: bool = True
    status: str = "ACTIVE"
    created_at: Optional[str] = None


class SecuritySummary(BaseModel):
    """Severity summary metrics for a security scan."""
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    total: int = 0


class SecurityScanResult(BaseModel):
    """Immutable audit evaluation outcome of a patch revision."""
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    patch_id: Optional[str] = None
    patch_revision: int = 1
    patch_hash: str
    base_commit_sha: Optional[str] = None
    status: str = SecurityGateStatus.UNVERIFIED.value
    can_approve: bool = False
    block_reasons: List[str] = Field(default_factory=list)
    findings: List[SecurityFindingSchema] = Field(default_factory=list)
    summary: SecuritySummary = Field(default_factory=SecuritySummary)
    scanners_executed: List[str] = Field(default_factory=list)
    scanners_available: Dict[str, bool] = Field(default_factory=dict)
    scanned_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: int = 0


class ScannerStatusItem(BaseModel):
    """Health and version reporting for an individual security scanner."""
    name: str
    category: str
    available: bool
    version: Optional[str] = None
    description: str
    mandatory: bool = True


class SecurityDiagnostics(BaseModel):
    """System-level diagnostic snapshot of the Security Guardian subsystem."""
    status: str = "healthy"
    policy_version: str = "1.0.0"
    mandatory_blockers_enforced: bool = True
    scanners: List[ScannerStatusItem] = Field(default_factory=list)
    active_policy_summary: str = "CRITICAL and HIGH findings, high-confidence credentials, and security regressions block human approval."
