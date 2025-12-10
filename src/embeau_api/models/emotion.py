"""Emotion analysis database models."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from embeau_api.db.session import Base


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class EmotionEntry(Base):
    """Individual emotion analysis entry."""

    __tablename__ = "emotion_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # User input
    input_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Emotion scores (0-100)
    anxiety: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    satisfaction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    happiness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    depression: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Healing colors recommended - stored as JSON string
    healing_colors: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array

    # RAG recommendation result
    rag_color_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rag_psychological_effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    rag_recommendation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rag_usage_method: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="emotion_entries")


class WeeklyInsight(Base):
    """Weekly aggregated insights for users."""

    __tablename__ = "weekly_insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Week range
    week_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    week_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Aggregated emotion distribution (averages)
    avg_anxiety: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_stress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_satisfaction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_happiness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_depression: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # AI-generated insights
    improvement: Mapped[str] = mapped_column(Text, nullable=False)
    next_week_suggestion: Mapped[str] = mapped_column(Text, nullable=False)

    # Statistics
    active_days: Mapped[int] = mapped_column(nullable=False, default=0)
    total_entries: Mapped[int] = mapped_column(nullable=False, default=0)
    color_improvement: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mood_improvement: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stress_relief: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


# Forward reference
from embeau_api.models.user import User  # noqa: E402, F811
