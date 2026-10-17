"""Pydantic V2 schemas for ReviewFinding and ReviewResponse."""
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

SeverityLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


class ReviewFinding(BaseModel):
    """An independent code review finding reported against a proposed patch."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique finding identifier, e.g. 'FIND-001'")
    severity: SeverityLevel = Field(..., description="Risk severity level")
    category: str = Field(..., description="Category, e.g. 'security', 'regression', 'correctness', 'style'")
    file_path: Optional[str] = Field(default=None, description="Repository relative file path")
    line_number: Optional[int] = Field(default=None, ge=1, description="Line number if localized")
    description: str = Field(..., description="Detailed description of the issue or risk")
    evidence: str = Field(..., description="Concrete code or test evidence demonstrating the finding")
    potential_impact: Optional[str] = Field(default=None, description="Potential consequence if left unaddressed")
    recommendation: str = Field(..., description="Actionable suggestion for remediation")


class ReviewResponse(BaseModel):
    """Evaluation summary produced by the independent Reviewer agent."""
    model_config = ConfigDict(extra="forbid")

    findings: list[ReviewFinding] = Field(default_factory=list, description="List of identified issues or observations")
    acceptance_criteria_met: bool = Field(..., description="Whether all issue acceptance criteria are satisfied")
    recommendation: Literal["approve", "request_changes", "reject"] = Field(
        ...,
        description="Technical recommendation (never overrides mandatory human approval)",
    )
    unresolved_risks: list[str] = Field(default_factory=list, description="Residual risks or unverified areas")
    run_id: Optional[str] = Field(default=None, description="Platform Run ID")
    repository_id: Optional[str] = Field(default=None, description="Repository identifier")
    patch_hash: Optional[str] = Field(default=None, description="SHA-256 hash of reviewed patch")
    canonical_patch_id: Optional[str] = Field(default=None, description="Composite canonical patch identity")
    base_commit_sha: Optional[str] = Field(default=None, description="Target base commit SHA")
    patch_revision: Optional[int] = Field(default=None, description="Revision number of reviewed patch")
    reviewed_at: Optional[str] = Field(default=None, description="Timestamp of review")
