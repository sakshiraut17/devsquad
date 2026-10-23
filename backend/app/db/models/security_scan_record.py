"""SecurityScanRecord database model storing historical security scan outcomes."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.run import Run
    from app.db.models.patch import Patch


class SecurityScanRecord(Base):
    """Immutable audit record representing a Security Guardian evaluation of a patch revision."""

    __tablename__ = "security_scan_records"

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
    patch_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("patches.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    patch_revision: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    patch_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    base_commit_sha: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        index=True,
        nullable=False,
    )
    findings_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    critical_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    high_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    medium_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    low_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    info_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    block_reasons: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    scanners_executed: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="security_scans",
    )
    patch: Mapped[Optional["Patch"]] = relationship(
        "Patch",
        back_populates="security_scans",
    )
