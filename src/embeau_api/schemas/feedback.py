"""Feedback schemas."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from embeau_api.schemas.base import BaseSchema

FeedbackRating = Literal[1, 2, 3, 4, 5]
FeedbackTargetType = Literal["color_result", "emotion_map", "healing_color", "recommendation"]


class FeedbackRequest(BaseSchema):
    """Feedback submission request."""

    rating: FeedbackRating
    target_type: FeedbackTargetType = Field(..., alias="targetType")
    target_id: str = Field(..., alias="targetId")
    comment: str | None = None
    timestamp: datetime | None = None


class FeedbackResponse(BaseSchema):
    """Feedback response."""

    id: str
    rating: FeedbackRating
    target_type: FeedbackTargetType = Field(..., alias="targetType")
    target_id: str = Field(..., alias="targetId")
    created_at: datetime = Field(..., alias="createdAt")
