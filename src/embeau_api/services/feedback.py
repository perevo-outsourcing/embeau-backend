"""Feedback service for collecting user feedback."""

from sqlalchemy.ext.asyncio import AsyncSession

from embeau_api.core.logging import research_logger
from embeau_api.models import Feedback
from embeau_api.schemas.feedback import FeedbackRequest, FeedbackResponse


class FeedbackService:
    """Service for handling user feedback."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def submit_feedback(self, user_id: str, data: FeedbackRequest) -> FeedbackResponse:
        """Submit user feedback."""
        feedback = Feedback(
            user_id=user_id,
            rating=data.rating,
            target_type=data.target_type,
            target_id=data.target_id,
            comment=data.comment,
        )
        self.db.add(feedback)
        await self.db.flush()

        # Log for research
        research_logger.log_feedback(
            user_id=user_id,
            rating=data.rating,
            target_type=data.target_type,
            target_id=data.target_id,
        )

        return FeedbackResponse(
            id=feedback.id,
            rating=feedback.rating,
            target_type=feedback.target_type,  # type: ignore
            target_id=feedback.target_id,
            created_at=feedback.created_at,
        )
