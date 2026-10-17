"""DevSquad Pydantic V2 Schemas Package."""
from app.schemas.plan import PlanStep, StructuredPlan
from app.schemas.patch import PatchItem, PatchResponse
from app.schemas.test_result import TestResult
from app.schemas.review import ReviewFinding, ReviewResponse, SeverityLevel
from app.schemas.approval import ApprovalRequest, ApprovalResponse
from app.schemas.health import ComponentHealth, ComponentStatus, HealthResponse
from app.schemas.user import UserCreate, UserResponse
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.schemas.issue import IssueCreate, IssueResponse
from app.schemas.run import RunCreate, RunResponse
from app.schemas.agent_event import AgentEvent

from app.schemas.repository_context import (
    ContextFile,
    ContextRetrievalLimitations,
    OmittedContextFile,
    RepositoryContext,
    TruncationMetadata,
)
from app.schemas.repair_registry import (
    FailedPatchEntry,
    FailedPatchRegistry,
)
from app.schemas.evidence import (
    EvidencePurpose,
    EvidenceReference,
    PlanVerificationIssue,
    PlanVerificationResult,
)

__all__ = [
    "PlanStep",
    "StructuredPlan",
    "PatchItem",
    "PatchResponse",
    "TestResult",
    "ReviewFinding",
    "ReviewResponse",
    "SeverityLevel",
    "ApprovalRequest",
    "ApprovalResponse",
    "ComponentHealth",
    "ComponentStatus",
    "HealthResponse",
    "UserCreate",
    "UserResponse",
    "RepositoryCreate",
    "RepositoryResponse",
    "IssueCreate",
    "IssueResponse",
    "RunCreate",
    "RunResponse",
    "AgentEvent",
    "ContextFile",
    "ContextRetrievalLimitations",
    "OmittedContextFile",
    "RepositoryContext",
    "TruncationMetadata",
    "FailedPatchEntry",
    "FailedPatchRegistry",
    "EvidencePurpose",
    "EvidenceReference",
    "PlanVerificationIssue",
    "PlanVerificationResult",
]
