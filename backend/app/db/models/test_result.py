import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.db.models.run import Run


class TestResult(Base):
    """TestResult model storing Docker sandbox test runner results."""

    __tablename__ = "test_results"
    __test__ = False  # Instruct pytest not to collect this SQLAlchemy model as a test class

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    exit_code: Mapped[int] = mapped_column(Integer, nullable=False)
    stdout: Mapped[str] = mapped_column(Text, nullable=True)
    stderr: Mapped[str] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    executed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    run: Mapped["Run"] = relationship("Run", back_populates="test_results")
