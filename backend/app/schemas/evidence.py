"""Strongly typed evidence reference and verification schemas for Grounded Planning."""
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.security import is_safe_relative_path


class EvidencePurpose(str, Enum):
    """Engineering purpose and semantic category of a code evidence citation."""
    ROOT_CAUSE = "root_cause"
    IMPLEMENTATION_TARGET = "implementation_target"
    DEPENDENCY = "dependency"
    TEST = "test"
    RISK = "risk"


class EvidenceReference(BaseModel):
    """
    Cryptographically grounded reference to a specific line range and content snapshot
    within the verified RepositoryContext.
    """
    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(..., description="Normalized relative repository file path")
    start_line: int = Field(..., ge=1, description="1-indexed starting line number (inclusive)")
    end_line: int = Field(..., ge=1, description="1-indexed ending line number (inclusive)")
    file_sha256: str = Field(..., min_length=7, max_length=64, description="SHA-256 hash of the entire cited file content")
    base_commit_sha: str = Field(..., min_length=7, max_length=64, description="Exact base commit SHA of the cited file")
    repo_owner: Optional[str] = Field(default=None, description="Repository owner / organization")
    repo_name: Optional[str] = Field(default=None, description="Repository name")
    repository_id: Optional[str] = Field(default=None, description="Repository database ID if bound")
    excerpt: Optional[str] = Field(default=None, description="Exact source code lines or symbol excerpt from cited span")
    symbol: Optional[str] = Field(default=None, description="Function, class, or symbol name")
    purpose: EvidencePurpose = Field(default=EvidencePurpose.ROOT_CAUSE, description="Engineering purpose of citation")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Cited file_path cannot be empty or whitespace.")
        if "\0" in v:
            raise ValueError("Cited file_path cannot contain null bytes.")
        norm = v.replace("\\", "/").strip()
        if not is_safe_relative_path(norm):
            raise ValueError(f"Cited file_path is not a safe relative path: '{v}'")
        return norm

    @model_validator(mode="after")
    def validate_line_span(self) -> "EvidenceReference":
        if self.start_line > self.end_line:
            raise ValueError(
                f"Invalid line span: start_line ({self.start_line}) cannot be greater than end_line ({self.end_line})"
            )
        return self


class PlanVerificationIssue(BaseModel):
    """An individual defect, mismatch, or fabrication detected during plan evidence verification."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Machine-readable issue code, e.g. 'OUT_OF_BOUNDS_LINE_SPAN'")
    message: str = Field(..., description="Human-readable explanation of why citation failed verification")
    citation_index: Optional[int] = Field(default=None, description="Index of offending citation if applicable")
    file_path: Optional[str] = Field(default=None, description="Affected file path")
    details: Optional[dict[str, Any]] = Field(default=None, description="Supplemental diagnostic metadata")


class PlanVerificationResult(BaseModel):
    """Deterministic result of evaluating all evidence references in a StructuredPlan."""
    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="True if 100% of evidence citations are mathematically and contextually verified")
    verified_citations_count: int = Field(default=0, ge=0)
    issues: List[PlanVerificationIssue] = Field(default_factory=list, description="List of verification failures")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings, e.g. citations from truncated files")
    error_summary: Optional[str] = Field(default=None, description="Combined summary of verification errors")
