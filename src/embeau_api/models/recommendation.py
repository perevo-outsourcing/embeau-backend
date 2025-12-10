"""Recommendation database models."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from embeau_api.db.session import Base


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class RecommendationCache(Base):
    """Cache for personalized recommendations."""

    __tablename__ = "recommendation_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Recommendation context
    color_hex: Mapped[str] = mapped_column(String(7), nullable=False)
    season: Mapped[str | None] = mapped_column(String(20), nullable=True)
    emotion_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cached recommendations - stored as JSON
    fashion_items: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    food_items: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    activity_items: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Cache metadata
    cache_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class RecommendationItem(Base):
    """Static recommendation items database."""

    __tablename__ = "recommendation_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Item details
    item_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # fashion, food, activity
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Color associations
    primary_color_hex: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    season: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    tone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Emotion associations
    emotion_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of emotions

    # Metadata
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
