import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.db.models.run import Run


class PullRequest(Base):
    """PullRequest model storing GitHub PRs created after human approval."""

    __tablename__ = "pull_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pr_url: Mapped[str] = mapped_column(String(500), nullable=False)
    head_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    base_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    run: Mapped["Run"] = relationship("Run", back_populates="pull_request")
