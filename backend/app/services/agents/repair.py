"""Repair cycle abstractions and persistence helpers for multi-agent workflows."""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.agent_log import AgentLog
from app.db.models.patch import Patch
from app.schemas.patch import PatchItem
from app.schemas.review import ReviewResponse
from app.schemas.test_result import TestResult

logger = logging.getLogger("devsquad.repair")


class RevisionRecord(BaseModel):
    """Immutable snapshot of an iteration in the Coder -> Tester -> Reviewer cycle."""
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(..., ge=1, description="Revision number")
    patch: PatchItem = Field(..., description="Generated and validated patch item")
    test_result: TestResult = Field(..., description="Sandbox or AST validation results")
    review: Optional[ReviewResponse] = Field(default=None, description="Independent review results")


class RepairCycleState(BaseModel):
    """Encapsulates the state and history of a bounded multi-revision repair loop."""
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., description="Associated platform Run ID")
    current_revision: int = Field(default=1, ge=1, description="Active revision counter")
    max_revisions: int = Field(default_factory=lambda: settings.max_agent_retries, ge=1, le=10)
    history: List[RevisionRecord] = Field(default_factory=list, description="Historical record of all revisions")
    is_terminal: bool = Field(default=False, description="Whether repair loop has concluded")
    terminal_status: Optional[str] = Field(default=None, description="Terminal status, e.g. 'AWAITING_APPROVAL', 'MAX_RETRIES_EXCEEDED'")

    def add_revision(self, patch: PatchItem, test_result: TestResult, review: Optional[ReviewResponse] = None) -> None:
        """Add an immutable record of a completed revision."""
        rec = RevisionRecord(
            revision=patch.revision,
            patch=patch,
            test_result=test_result,
            review=review,
        )
        self.history.append(rec)
        self.current_revision = patch.revision + 1
        if self.current_revision > self.max_revisions:
            self.is_terminal = True
            self.terminal_status = "MAX_RETRIES_EXCEEDED"

    def get_latest_feedback(self) -> Optional[str]:
        """Compile feedback from the most recent revision for the Coder agent."""
        if not self.history:
            return None
        latest = self.history[-1]
        feedback_lines: List[str] = []

        if latest.test_result.status != "TESTS_PASSED" and latest.test_result.status != "PARTIAL_VALIDATION":
            feedback_lines.append(f"Test Execution Failed: {latest.test_result.status}")
            if latest.test_result.failure_summary:
                feedback_lines.append(f"Failure Summary: {latest.test_result.failure_summary}")
            if latest.test_result.stderr:
                feedback_lines.append(f"Error Output:\n{latest.test_result.stderr[:500]}")

        if latest.review:
            feedback_lines.append(f"Review Recommendation: {latest.review.recommendation}")
            for f in latest.review.findings:
                if f.severity in ("CRITICAL", "HIGH", "MEDIUM"):
                    feedback_lines.append(
                        f"Finding [{f.severity}] {f.category} in {f.file_path or 'patch'}: {f.description}. "
                        f"Recommended: {f.recommendation}"
                    )

        return "\n".join(feedback_lines) if feedback_lines else None


# --- Persistence Service Helpers ---

async def record_patch_revision(
    session: AsyncSession,
    run_id: str,
    patch_item: PatchItem,
    validation_status: str = "PENDING_VALIDATION",
) -> Patch:
    """Persist an immutable Patch entity record to the database."""
    patch_entity = Patch(
        run_id=run_id,
        revision=patch_item.revision,
        unified_diff=patch_item.unified_diff,
        target_files=patch_item.target_files,
        summary=patch_item.summary,
        content_hash=patch_item.content_hash,
        validation_status=validation_status,
    )
    session.add(patch_entity)
    await session.commit()
    await session.refresh(patch_entity)
    logger.info(
        f"Persisted patch revision {patch_item.revision} for run {run_id} (hash: {patch_item.content_hash[:8]})"
    )
    return patch_entity


async def log_agent_event(
    session: AsyncSession,
    run_id: str,
    agent_name: str,
    event_type: str,
    message: str,
    input_summary: Optional[str] = None,
    output_summary: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> AgentLog:
    """Persist an immutable audit AgentLog record for run traceability."""
    agent_log = AgentLog(
        run_id=run_id,
        agent_name=agent_name,
        event_type=event_type,
        message=message,
        input_summary=input_summary,
        output_summary=output_summary,
        duration_ms=duration_ms,
    )
    session.add(agent_log)
    await session.commit()
    await session.refresh(agent_log)
    return agent_log

