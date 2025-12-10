"""User action log models for research data collection."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from embeau_api.db.session import Base


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class UserActionLog(Base):
    """Detailed user action logs for research analysis.

    This model captures all user interactions for academic research purposes.
    Logs are structured to enable quantitative analysis of user behavior
    patterns, engagement metrics, and therapeutic effectiveness.
    """

    __tablename__ = "user_action_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    session_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)

    # Action details
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    # Context
    page_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referrer_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Device information
    device_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # mobile, desktop, tablet
    browser: Mapped[str | None] = mapped_column(String(100), nullable=True)
    os: Mapped[str | None] = mapped_column(String(100), nullable=True)
    screen_resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Performance metrics
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="action_logs")


class ResearchDataExport(Base):
    """Track research data exports for audit trail."""

    __tablename__ = "research_data_exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    researcher_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Export details
    export_type: Mapped[str] = mapped_column(String(50), nullable=False)  # full, anonymized, aggregated
    data_range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # File info
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


# Forward reference
from embeau_api.models.user import User  # noqa: E402, F811
