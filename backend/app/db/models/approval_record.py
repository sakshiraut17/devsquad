"""ApprovalRecord database model ensuring tamper-evident human decision auditing."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.run import Run
    from app.db.models.patch import Patch
    from app.db.models.user import User


class ApprovalRecord(Base):
    """
    Immutable audit record for human approval or rejection of a specific patch revision.
    Binds the human decision explicitly to the patch content hash and validation evidence.
    """

    __tablename__ = "approval_records"

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
    approver_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    decision: Mapped[str] = mapped_column(
        String(20),  # "approved" or "rejected"
        nullable=False,
    )
    patch_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    validation_evidence: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="approval_records",
    )
    patch: Mapped["Patch"] = relationship(
        "Patch",
        back_populates="approval_records",
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="approvals",
    )
