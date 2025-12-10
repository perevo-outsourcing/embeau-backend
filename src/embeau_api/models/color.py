"""Color analysis database models."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from embeau_api.db.session import Base


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class ColorResult(Base):
    """Personal color analysis result."""

    __tablename__ = "color_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Color Analysis Results
    season: Mapped[str] = mapped_column(String(20), nullable=False)  # spring, summer, autumn, winter
    tone: Mapped[str] = mapped_column(String(20), nullable=False)  # warm, cool
    subtype: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., "Summer_Cool"
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Recommended colors stored as JSON string
    recommended_colors: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array

    # Emotion detected during analysis
    facial_expression: Mapped[str | None] = mapped_column(String(50), nullable=True)
    facial_expression_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Raw analysis data for research
    raw_analysis_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # Full JSON response

    # Timestamps
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="color_result")


class DailyHealingColor(Base):
    """Daily healing color recommendations."""

    __tablename__ = "daily_healing_colors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Healing color
    color_name: Mapped[str] = mapped_column(String(100), nullable=False)
    color_hex: Mapped[str] = mapped_column(String(7), nullable=False)
    color_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Effects and recommendations
    calm_effect: Mapped[str] = mapped_column(Text, nullable=False)
    personal_fit: Mapped[str] = mapped_column(Text, nullable=False)
    daily_affirmation: Mapped[str] = mapped_column(Text, nullable=False)

    # Date for this recommendation
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Generated based on
    based_on_emotion_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


# Forward reference
from embeau_api.models.user import User  # noqa: E402, F811
