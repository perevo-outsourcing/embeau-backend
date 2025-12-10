"""Research-grade logging system for academic paper data collection."""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ActionType(str, Enum):
    """User action types for research logging."""

    # Authentication
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"

    # Color Analysis
    COLOR_ANALYZE_START = "color.analyze.start"
    COLOR_ANALYZE_COMPLETE = "color.analyze.complete"
    COLOR_RESULT_VIEW = "color.result.view"
    DAILY_HEALING_VIEW = "color.daily_healing.view"

    # Emotion Analysis
    EMOTION_ANALYZE_START = "emotion.analyze.start"
    EMOTION_ANALYZE_COMPLETE = "emotion.analyze.complete"
    EMOTION_HISTORY_VIEW = "emotion.history.view"

    # Recommendations
    RECOMMENDATION_VIEW = "recommendation.view"
    RECOMMENDATION_CLICK = "recommendation.click"

    # Insights
    WEEKLY_INSIGHT_VIEW = "insight.weekly.view"
    REPORT_DOWNLOAD = "insight.report.download"

    # Feedback
    FEEDBACK_SUBMIT = "feedback.submit"

    # Navigation
    PAGE_VIEW = "navigation.page_view"
    SESSION_START = "session.start"
    SESSION_END = "session.end"


class ResearchLog(BaseModel):
    """Structured log entry for research data collection."""

    timestamp: datetime
    user_id: str | None
    session_id: str | None
    action_type: ActionType
    action_data: dict[str, Any]
    device_info: dict[str, Any] | None = None
    duration_ms: int | None = None


class ResearchLogger:
    """Logger specifically designed for research paper data collection.

    Captures structured data about user interactions with the app,
    enabling quantitative analysis for academic research.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("embeau.research")
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure the research logger."""
        handler = logging.FileHandler("research_logs.jsonl", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log(
        self,
        action_type: ActionType,
        user_id: str | UUID | None = None,
        session_id: str | None = None,
        action_data: dict[str, Any] | None = None,
        device_info: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> ResearchLog:
        """Log a research event."""
        log_entry = ResearchLog(
            timestamp=datetime.now(timezone.utc),
            user_id=str(user_id) if user_id else None,
            session_id=session_id,
            action_type=action_type,
            action_data=action_data or {},
            device_info=device_info,
            duration_ms=duration_ms,
        )
        self.logger.info(log_entry.model_dump_json())
        return log_entry

    def log_color_analysis(
        self,
        user_id: str | UUID,
        result: dict[str, Any],
        duration_ms: int,
        session_id: str | None = None,
    ) -> None:
        """Log a color analysis event with full result data."""
        self.log(
            action_type=ActionType.COLOR_ANALYZE_COMPLETE,
            user_id=user_id,
            session_id=session_id,
            action_data={
                "season": result.get("season"),
                "tone": result.get("tone"),
                "confidence": result.get("confidence"),
            },
            duration_ms=duration_ms,
        )

    def log_emotion_analysis(
        self,
        user_id: str | UUID,
        input_text: str,
        emotions: dict[str, float],
        healing_colors: list[dict[str, Any]],
        duration_ms: int,
        session_id: str | None = None,
    ) -> None:
        """Log an emotion analysis event with anonymized text hash."""
        self.log(
            action_type=ActionType.EMOTION_ANALYZE_COMPLETE,
            user_id=user_id,
            session_id=session_id,
            action_data={
                "input_length": len(input_text),
                "emotions": emotions,
                "healing_color_count": len(healing_colors),
                "primary_healing_color": healing_colors[0]["hex"] if healing_colors else None,
            },
            duration_ms=duration_ms,
        )

    def log_feedback(
        self,
        user_id: str | UUID,
        rating: int,
        target_type: str,
        target_id: str,
        session_id: str | None = None,
    ) -> None:
        """Log user feedback for effectiveness analysis."""
        self.log(
            action_type=ActionType.FEEDBACK_SUBMIT,
            user_id=user_id,
            session_id=session_id,
            action_data={
                "rating": rating,
                "target_type": target_type,
                "target_id": target_id,
            },
        )


# Global research logger instance
research_logger = ResearchLogger()
