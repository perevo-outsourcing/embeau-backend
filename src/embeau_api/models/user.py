"""User database models."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from embeau_api.db.session import Base


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class User(Base):
    """User model for research participants."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    participant_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Research metadata
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    color_result: Mapped["ColorResult | None"] = relationship(
        "ColorResult", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    emotion_entries: Mapped[list["EmotionEntry"]] = relationship(
        "EmotionEntry", back_populates="user", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan"
    )
    action_logs: Mapped[list["UserActionLog"]] = relationship(
        "UserActionLog", back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    """User session for tracking research sessions."""

    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Session metadata
    device_info: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Forward references for relationships
from embeau_api.models.color import ColorResult  # noqa: E402
from embeau_api.models.emotion import EmotionEntry  # noqa: E402
from embeau_api.models.feedback import Feedback  # noqa: E402
from embeau_api.models.log import UserActionLog  # noqa: E402
