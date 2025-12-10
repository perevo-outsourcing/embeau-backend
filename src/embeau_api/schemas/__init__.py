"""Pydantic schemas for EMBEAU API."""

from embeau_api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from embeau_api.schemas.base import ApiResponse, ErrorDetail, PaginatedResponse
from embeau_api.schemas.color import (
    ColorAnalyzeRequest,
    ColorItem,
    DailyHealingColorResponse,
    PersonalColorResult,
)
from embeau_api.schemas.emotion import (
    EmotionAnalyzeRequest,
    EmotionEntry,
    EmotionState,
    HealingColor,
    WeeklyInsightResponse,
)
from embeau_api.schemas.feedback import FeedbackRequest, FeedbackResponse
from embeau_api.schemas.recommendation import Recommendation, RecommendationItem

__all__ = [
    # Base
    "ApiResponse",
    "ErrorDetail",
    "PaginatedResponse",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    # Color
    "ColorAnalyzeRequest",
    "ColorItem",
    "DailyHealingColorResponse",
    "PersonalColorResult",
    # Emotion
    "EmotionAnalyzeRequest",
    "EmotionEntry",
    "EmotionState",
    "HealingColor",
    "WeeklyInsightResponse",
    # Recommendation
    "Recommendation",
    "RecommendationItem",
    # Feedback
    "FeedbackRequest",
    "FeedbackResponse",
]
