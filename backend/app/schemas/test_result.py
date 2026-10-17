"""Pydantic V2 schema for TestResult representing sandbox execution outcomes."""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TestResult(BaseModel):
    """Detailed execution results captured from Docker sandbox or static fallback."""
    __test__ = False
    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        ...,
        description="Execution status, e.g. TESTS_PASSED, TESTS_FAILED, SYNTAX_VALIDATION_PASSED, SANDBOX_UNAVAILABLE, EXECUTION_TIMEOUT",
    )
    environment: str = Field(..., description="Execution environment, e.g. 'docker_container' or 'host_ast_fallback'")
    commands_executed: list[str] = Field(default_factory=list, description="Commands run inside the sandbox")
    exit_code: Optional[int] = Field(default=None, description="Process exit code if executed")
    passed: Optional[int] = Field(default=None, ge=0, description="Number of passed tests")
    failed: Optional[int] = Field(default=None, ge=0, description="Number of failed tests")
    skipped: Optional[int] = Field(default=None, ge=0, description="Number of skipped tests")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    duration_ms: int = Field(default=0, ge=0, description="Total execution duration in milliseconds")
    failure_summary: Optional[str] = Field(default=None, description="Concise explanation of the test failure")
    security_limitations: list[str] = Field(
        default_factory=list,
        description="Security constraints applied, e.g. network disabled, non-root, read-only rootfs",
    )
    patch_hash: Optional[str] = Field(default=None, description="SHA-256 hash of the tested patch")
    patch_revision: Optional[int] = Field(default=None, description="Revision number of the tested patch")
    base_commit_sha: Optional[str] = Field(default=None, description="Base commit SHA or ref tested against")
    run_id: Optional[str] = Field(default=None, description="Platform Run ID")
    repository_id: Optional[str] = Field(default=None, description="Repository identifier")
    canonical_patch_id: Optional[str] = Field(default=None, description="Composite canonical patch identity")
    validation_status: Optional[str] = Field(default=None, description="Standard validation outcome status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when tests were executed",
    )

