"""Feedback database models."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from embeau_api.db.session import Base


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class Feedback(Base):
    """User feedback for research analysis."""

    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Rating (1-5 stars)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    # Target of feedback
    target_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # color_result, emotion_map, healing_color, recommendation
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Optional comment
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="feedbacks")


# Forward reference
from embeau_api.models.user import User  # noqa: E402, F811
