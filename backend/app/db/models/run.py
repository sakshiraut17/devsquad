import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.db.models.repository import Repository
    from app.db.models.issue import Issue
    from app.db.models.agent_log import AgentLog
    from app.db.models.patch import Patch
    from app.db.models.test_result import TestResult
    from app.db.models.pull_request import PullRequest


class Run(Base):
    """Run table model representing a workflow execution run for an issue."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    issue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("issues.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True, nullable=False
    )  # pending, planner_running, coder_running, tester_running, reviewer_running, awaiting_approval, pr_creating, completed, failed
    current_node: Mapped[str] = mapped_column(String(50), default="planner", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0000, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="runs")
    issue: Mapped["Issue"] = relationship("Issue", back_populates="runs")
    logs: Mapped[List["AgentLog"]] = relationship(
        "AgentLog", back_populates="run", cascade="all, delete-orphan"
    )
    patches: Mapped[List["Patch"]] = relationship(
        "Patch", back_populates="run", cascade="all, delete-orphan"
    )
    test_results: Mapped[List["TestResult"]] = relationship(
        "TestResult", back_populates="run", cascade="all, delete-orphan"
    )
    pull_request: Mapped[Optional["PullRequest"]] = relationship(
        "PullRequest", back_populates="run", uselist=False, cascade="all, delete-orphan"
    )
