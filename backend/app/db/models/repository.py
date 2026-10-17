"""Repository database model."""
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.issue import Issue
    from app.db.models.run import Run


class Repository(Base, TimestampMixin):
    """Monitored or integrated GitHub repository entity."""

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    github_repository_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    default_branch: Mapped[str] = mapped_column(
        String(100),
        default="main",
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="repositories",
    )
    issues: Mapped[list["Issue"]] = relationship(
        "Issue",
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list["Run"]] = relationship(
        "Run",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_repos_full_name_active", "full_name", "is_active"),
    )
