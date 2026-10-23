"""Typed LangGraph workflow state definitions, enums, and transition validators."""

from datetime import datetime, timezone
import enum
from typing import Any, Dict, List, Literal, Optional, TypedDict
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.schemas.patch import PatchItem
from app.schemas.plan import StructuredPlan
from app.schemas.review import ReviewResponse
from app.schemas.test_result import TestResult


class WorkflowStatus(str, enum.Enum):
    """Allowed top-level lifecycle states for an orchestrated workflow run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"


class WorkflowStage(str, enum.Enum):
    """Distinct execution stages in the multi-agent graph."""
    INPUT_VALIDATION = "INPUT_VALIDATION"
    CONTEXT_PREPARATION = "CONTEXT_PREPARATION"
    PLANNING = "PLANNING"
    CODING = "CODING"
    SECURITY_SCANNING = "SECURITY_SCANNING"
    TESTING = "TESTING"
    REVIEWING = "REVIEWING"
    REPAIRING = "REPAIRING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    FINALIZING = "FINALIZING"


class DevSquadState(TypedDict, total=False):
    """LangGraph-compatible state container coordinating multi-agent execution."""
    run_id: str
    thread_id: str
    repository_id: str
    issue_id: str
    status: str
    current_stage: str
    plan: Optional[Dict[str, Any]]
    current_patch: Optional[Dict[str, Any]]
    patch_revision: int
    security_result: Optional[Dict[str, Any]]
    test_result: Optional[Dict[str, Any]]
    review_result: Optional[Dict[str, Any]]
    repair_attempts: int
    max_repair_attempts: int
    approval_status: str
    validation_status: str
    error_code: Optional[str]
    error_message: Optional[str]
    started_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]
    resume_stage: Optional[str]
    metadata: Dict[str, Any]
    repair_feedback: Optional[str]
    repository_context: Optional[Dict[str, Any]]
    failed_patch_registry: Optional[List[Dict[str, Any]]]


def create_initial_state(
    run_id: str,
    repository_id: str,
    issue_id: str,
    max_repair_attempts: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> DevSquadState:
    """Factory creating an initial, sanitized DevSquadState dictionary."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return DevSquadState(
        run_id=run_id,
        thread_id=f"thread-{run_id}",
        repository_id=repository_id,
        issue_id=issue_id,
        status=WorkflowStatus.PENDING.value,
        current_stage=WorkflowStage.INPUT_VALIDATION.value,
        plan=None,
        current_patch=None,
        patch_revision=0,
        security_result=None,
        test_result=None,
        review_result=None,
        repair_attempts=0,
        max_repair_attempts=max_repair_attempts or settings.max_agent_retries,
        approval_status="PENDING",
        validation_status="NOT_STARTED",
        error_code=None,
        error_message=None,
        started_at=now_iso,
        updated_at=now_iso,
        completed_at=None,
        resume_stage=None,
        metadata=metadata or {},
        repair_feedback=None,
        repository_context=None,
        failed_patch_registry=[],
    )
