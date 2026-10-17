"""Issue database model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.db.models.repository import Repository
    from app.db.models.run import Run


class Issue(Base, TimestampMixin):
    """GitHub issue entity ingested for workflow execution."""

    __tablename__ = "issues"

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
    github_issue_number: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    state: Mapped[str] = mapped_column(
        String(50),
        default="open",
        nullable=False,
    )
    labels: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    html_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="issues",
    )
    runs: Mapped[list["Run"]] = relationship(
        "Run",
        back_populates="issue",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "github_issue_number",
            name="uq_repository_issue_number",
        ),
    )
