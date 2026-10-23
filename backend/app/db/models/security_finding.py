"""SecurityFinding database model representing detected security issues."""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.run import Run
    from app.db.models.patch import Patch


class SecuritySeverity(str, enum.Enum):
    """Normalized security finding severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class SecurityCategory(str, enum.Enum):
    """Categorization for detected security risks."""
    SECRET_EXPOSURE = "secret_exposure"
    SOURCE_VULNERABILITY = "source_vulnerability"
    DEPENDENCY_AUDIT = "dependency_audit"
    SECURITY_REGRESSION = "security_regression"
    PATCH_SCOPE = "patch_scope"


class SecurityFinding(Base):
    """Structured security finding discovered by the AI Security Guardian."""

    __tablename__ = "security_findings"

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
    category: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    rule_id: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False,
    )
    confidence: Mapped[str] = mapped_column(
        String(20),
        default="HIGH",
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    line_start: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    line_end: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    evidence_redacted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    remediation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    scanner_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    scanner_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    advisory_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    is_blocking: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
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
        back_populates="security_findings",
    )
    patch: Mapped[Optional["Patch"]] = relationship(
        "Patch",
        back_populates="security_findings",
    )
