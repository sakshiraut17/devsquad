"""Strongly typed repository context and provenance schemas."""
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.security import compute_sha256, is_safe_relative_path

# Standard 7 to 40 hex character git commit SHA regex
COMMIT_SHA_REGEX = re.compile(r"^[0-9a-fA-F]{7,40}$")


class ContextFile(BaseModel):
    """An individual file selected for repository context with cryptographic provenance."""
    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Normalized repository-relative file path")
    content: str = Field(..., description="UTF-8 decoded file content")
    sha256: str = Field(..., description="Cryptographic SHA-256 hash of the content")
    content_hash: str = Field(..., description="Backward-compatible alias for sha256")
    commit_sha: str = Field(..., description="Exact immutable commit SHA from which this file was retrieved")
    size_bytes: int = Field(..., ge=0, description="Size of file content in bytes")
    estimated_tokens: int = Field(..., ge=0, description="Estimated token count (~4 characters per token)")
    relevance_score: float = Field(default=1.0, description="Computed relevance score")
    selection_explanation: str = Field(default="", description="Reason for file selection")
    is_truncated: bool = Field(default=False, description="Whether individual file content was truncated")

    @field_validator("path")
    @classmethod
    def validate_path_safety(cls, v: str) -> str:
        """Strictly validate file path safety against traversal, absolute paths, and null bytes."""
        if not v or not v.strip():
            raise ValueError("File path cannot be empty or whitespace.")

        if "\0" in v:
            raise ValueError("File path cannot contain null bytes.")

        norm = v.replace("\\", "/").strip()

        # Reject absolute paths (UNIX or Windows drive letter)
        if norm.startswith("/"):
            raise ValueError(f"Path must be relative, cannot start with '/': '{v}'")

        if re.match(r"^[a-zA-Z]:", norm):
            raise ValueError(f"Path must be relative, cannot contain drive letter: '{v}'")

        # Reject directory traversal segments
        parts = norm.split("/")
        if ".." in parts or "." in parts:
            raise ValueError(f"Path traversal characters ('.' or '..') are forbidden: '{v}'")

        if not is_safe_relative_path(norm):
            raise ValueError(f"Path fails security relative path validation: '{v}'")

        return norm

    @model_validator(mode="before")
    @classmethod
    def sync_hashes_before_validation(cls, data: Any) -> Any:
        """Allow callers to pass either sha256 or content_hash interchangeably."""
        if isinstance(data, dict):
            if "sha256" in data and "content_hash" not in data:
                data["content_hash"] = data["sha256"]
            elif "content_hash" in data and "sha256" not in data:
                data["sha256"] = data["content_hash"]
        return data

    @model_validator(mode="after")
    def verify_hash_integrity(self) -> "ContextFile":
        """Verify that the provided sha256 hash strictly matches the computed hash of the content."""
        computed = compute_sha256(self.content)
        if self.sha256 != computed:
            raise ValueError(
                f"Content hash mismatch for '{self.path}': declared sha256 '{self.sha256}' "
                f"does not match computed sha256 '{computed}'."
            )
        if self.content_hash != self.sha256:
            raise ValueError(
                f"Inconsistent hash fields for '{self.path}': sha256='{self.sha256}' != content_hash='{self.content_hash}'"
            )
        return self


class OmittedContextFile(BaseModel):
    """A file considered during ranking but omitted from context with explicit rationale."""
    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Repository relative file path")
    reason: str = Field(..., description="Explicit reason (e.g. 'budget_exhausted', 'binary', 'vendored')")
    size_bytes: Optional[int] = Field(default=None, description="Discovered file size if available")


class TruncationMetadata(BaseModel):
    """Explicit metrics capturing context boundaries and truncation state."""
    model_config = ConfigDict(extra="forbid")

    is_truncated: bool = Field(..., description="Whether context budget or limits caused truncation")
    total_files_in_tree: int = Field(..., ge=0, description="Total files discovered in repository tree")
    total_bytes_in_tree: int = Field(..., ge=0, description="Total size in bytes discovered in repository tree")
    selected_files_count: int = Field(..., ge=0, description="Number of files included in context")
    omitted_files_count: int = Field(..., ge=0, description="Number of files excluded or omitted")
    budget_bytes: int = Field(..., gt=0, description="Max allowed context budget in bytes")
    consumed_bytes: int = Field(..., ge=0, description="Actual bytes consumed by selected files")
    estimated_total_tokens: int = Field(..., ge=0, description="Sum of estimated tokens for selected files")
    truncation_reasons: List[str] = Field(default_factory=list, description="Explicit reasons for omitted or truncated content")


class ContextRetrievalLimitations(BaseModel):
    """Disclosures regarding context limits and assumptions for downstream agents."""
    model_config = ConfigDict(extra="forbid")

    max_budget_bytes: int = Field(..., gt=0, description="Configured budget ceiling in bytes")
    excluded_patterns: List[str] = Field(default_factory=list, description="Directories and file patterns systematically ignored")
    retrieval_strategy: str = Field(..., description="Strategy used: 'github_live_tree', 'test_fixture', etc.")
    is_partial_representation: bool = Field(
        ...,
        description="True if selected files do not represent full repository",
    )
    warnings: List[str] = Field(default_factory=list, description="Advisories for downstream agents")


class RepositoryContext(BaseModel):
    """
    Cryptographically grounded, immutable repository snapshot providing provenance
    and context boundaries to multi-agent workflows.
    """
    model_config = ConfigDict(extra="forbid")

    repo_owner: str = Field(..., description="Repository owner or organization")
    repo_name: str = Field(..., description="Repository name")
    target_branch: str = Field(..., description="Target git branch (e.g. main, master)")
    base_commit_sha: str = Field(..., description="Exact immutable base git commit SHA")
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO timestamp")
    is_fixture: bool = Field(default=False, description="Flag indicating synthetic or test fixture context")
    fixture_identifier: Optional[str] = Field(default=None, description="Explicit identifier if is_fixture is True")
    selected_files: List[ContextFile] = Field(default_factory=list, description="Selected ranked files with provenance")
    omitted_files: List[OmittedContextFile] = Field(default_factory=list, description="Files considered but excluded")
    truncation: TruncationMetadata = Field(..., description="Explicit truncation metrics")
    limitations: ContextRetrievalLimitations = Field(..., description="Retrieval limitations and warnings")
    summary: str = Field(..., description="Human and agent-readable summary of context selection")

    @property
    def repo_full_name(self) -> str:
        return f"{self.repo_owner}/{self.repo_name}"

    @model_validator(mode="after")
    def validate_provenance_and_revision_consistency(self) -> "RepositoryContext":
        """
        Enforce strict cryptographic provenance and prevent mixing files across multiple commits.
        """
        # 1. Provenance check: fixture vs production
        if not self.is_fixture:
            lower_sha = self.base_commit_sha.lower()
            if "fixture" in lower_sha or "mock" in lower_sha:
                raise ValueError(
                    f"Synthetic commit SHA '{self.base_commit_sha}' is forbidden when is_fixture=False."
                )
            if not COMMIT_SHA_REGEX.match(self.base_commit_sha):
                raise ValueError(
                    f"Production context requires a valid 7-40 hex character commit SHA, got: '{self.base_commit_sha}'"
                )
        else:
            if not self.fixture_identifier or not self.fixture_identifier.strip():
                raise ValueError(
                    "Fixture context must have an explicit, non-empty 'fixture_identifier'."
                )

        # 2. Strict revision consistency: every selected file MUST match base_commit_sha
        for f in self.selected_files:
            if f.commit_sha != self.base_commit_sha:
                raise ValueError(
                    f"Commit revision mismatch in file '{f.path}': file commit '{f.commit_sha}' "
                    f"does not match base commit '{self.base_commit_sha}'. "
                    f"Mixing commits within a single RepositoryContext snapshot is prohibited."
                )

        return self

    def verify_integrity(self) -> bool:
        """
        Exhaustively verify path safety, content hashes, and revision consistency.
        Raises ValueError if any corruption, tampering, or mismatch is detected.
        """
        for f in self.selected_files:
            # Re-verify path safety
            if not is_safe_relative_path(f.path):
                raise ValueError(f"Unsafe file path detected in context: '{f.path}'")

            # Re-verify SHA256 content hash
            computed = compute_sha256(f.content)
            if f.sha256 != computed:
                raise ValueError(
                    f"Integrity check failed: content hash mismatch for '{f.path}'. "
                    f"Declared '{f.sha256}', computed '{computed}'."
                )

            # Re-verify commit revision
            if f.commit_sha != self.base_commit_sha:
                raise ValueError(
                    f"Integrity check failed: commit mismatch for '{f.path}'. "
                    f"File commit '{f.commit_sha}' != base commit '{self.base_commit_sha}'."
                )

        return True
