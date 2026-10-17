"""Failed patch registry preventing duplicate failing patch attempts in repair cycles."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FailedPatchEntry(BaseModel):
    """Immutable record of an individual patch attempt that failed validation or review."""
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., description="Platform Run ID")
    repository_id: str = Field(..., description="Repository identifier")
    base_commit_sha: str = Field(..., description="Target base Git commit SHA")
    patch_hash: str = Field(..., description="Canonical SHA-256 hash of the unified diff")
    canonical_patch_id: str = Field(..., description="Composite canonical patch identity '<sha>:<hash>'")
    revision: int = Field(..., ge=1, description="Patch revision number that failed")
    failure_category: str = Field(..., description="Failure category: 'TEST_FAILED', 'SYNTAX_ERROR', 'REVIEW_REJECTED', 'CRITICAL_FINDINGS'")
    diagnostic_fingerprint: str = Field(..., description="Concise diagnostic summary or compiler error fingerprint")
    validation_environment: str = Field(default="default", description="Environment in which failure occurred")
    recorded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary diagnostic metadata")


class FailedPatchRegistry(BaseModel):
    """
    Bounded registry tracking historical failed patches to prevent the repair loop
    from generating and testing identical failing patches under equivalent conditions.
    """
    model_config = ConfigDict(extra="forbid")

    entries: List[FailedPatchEntry] = Field(default_factory=list, description="Historical list of failed patch attempts")

    def is_duplicate_failed_patch(
        self,
        run_id: str,
        base_commit_sha: str,
        patch_hash: str,
        environment: Optional[str] = None,
    ) -> Optional[FailedPatchEntry]:
        """
        Check if an identical patch has already failed under equivalent circumstances.
        Only matches when run_id, base_commit_sha, and patch_hash match.
        Does NOT block identical hashes in different runs or against different base commits.
        """
        clean_sha = base_commit_sha.strip().lower()
        for entry in self.entries:
            if (
                entry.run_id == run_id
                and entry.base_commit_sha.strip().lower() == clean_sha
                and entry.patch_hash == patch_hash
            ):
                # If environment is given and different, this is a distinct execution context
                if environment and entry.validation_environment and entry.validation_environment != environment:
                    continue
                return entry
        return None

    def record_failure(
        self,
        run_id: str,
        repository_id: str,
        base_commit_sha: str,
        patch_hash: str,
        revision: int,
        failure_category: str,
        diagnostic_fingerprint: str,
        validation_environment: str = "default",
        details: Optional[Dict[str, Any]] = None,
        max_entries: int = 50,
    ) -> FailedPatchEntry:
        """Record a new failed patch attempt, bounding total entries to prevent unbounded state growth."""
        canonical_id = f"{base_commit_sha.strip().lower()}:{patch_hash}"
        entry = FailedPatchEntry(
            run_id=run_id,
            repository_id=repository_id,
            base_commit_sha=base_commit_sha.strip().lower(),
            patch_hash=patch_hash,
            canonical_patch_id=canonical_id,
            revision=revision,
            failure_category=failure_category,
            diagnostic_fingerprint=diagnostic_fingerprint[:255] if diagnostic_fingerprint else "unspecified failure",
            validation_environment=validation_environment,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            details=details or {},
        )
        self.entries.append(entry)
        if len(self.entries) > max_entries:
            self.entries = self.entries[-max_entries:]
        return entry
