"""PullRequest database model."""
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.run import Run
    from app.db.models.patch import Patch


class PullRequest(Base, TimestampMixin):
    """GitHub Pull Request generated following authorized human approval."""

    __tablename__ = "pull_requests"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    patch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patches.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    github_pr_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        index=True,
        nullable=True,
    )
    html_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    target_branch: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="created",
        nullable=False,
    )

    # Relationships
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="pull_requests",
    )
    patch: Mapped["Patch"] = relationship(
        "Patch",
        back_populates="pull_requests",
    )
