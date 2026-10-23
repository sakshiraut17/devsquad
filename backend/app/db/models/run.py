"""Run database model tracking workflow executions."""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.repository import Repository
    from app.db.models.issue import Issue
    from app.db.models.patch import Patch
    from app.db.models.agent_log import AgentLog
    from app.db.models.pull_request import PullRequest
    from app.db.models.approval_record import ApprovalRecord
    from app.db.models.security_finding import SecurityFinding
    from app.db.models.security_scan_record import SecurityScanRecord


class RunStatus(str, enum.Enum):
    """Allowed lifecycle states for a DevSquad execution run."""
    QUEUED = "QUEUED"
    INGESTING = "INGESTING"
    PLANNING = "PLANNING"
    CODING = "CODING"
    SECURITY_SCANNING = "SECURITY_SCANNING"
    TESTING = "TESTING"
    REVIEWING = "REVIEWING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CREATING_PR = "CREATING_PR"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Run(Base, TimestampMixin):
    """Multi-agent execution run entity."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=RunStatus.QUEUED.value,
        index=True,
        nullable=False,
    )
    current_node: Mapped[str] = mapped_column(
        String(100),
        default="start",
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="runs",
    )
    issue: Mapped["Issue"] = relationship(
        "Issue",
        back_populates="runs",
    )
    patches: Mapped[list["Patch"]] = relationship(
        "Patch",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="Patch.revision",
    )
    agent_logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentLog.created_at",
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(
        "PullRequest",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    approval_records: Mapped[list["ApprovalRecord"]] = relationship(
        "ApprovalRecord",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ApprovalRecord.created_at",
    )
    security_findings: Mapped[list["SecurityFinding"]] = relationship(
        "SecurityFinding",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="SecurityFinding.created_at",
    )
    security_scans: Mapped[list["SecurityScanRecord"]] = relationship(
        "SecurityScanRecord",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="SecurityScanRecord.created_at",
    )
