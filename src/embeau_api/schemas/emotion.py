"""Emotion analysis schemas."""

from datetime import datetime

from pydantic import Field

from embeau_api.schemas.base import BaseSchema
from embeau_api.schemas.color import ColorItem


class EmotionState(BaseSchema):
    """Emotion state with scores for each dimension."""

    anxiety: float = Field(..., ge=0, le=100)
    stress: float = Field(..., ge=0, le=100)
    satisfaction: float = Field(..., ge=0, le=100)
    happiness: float = Field(..., ge=0, le=100)
    depression: float = Field(..., ge=0, le=100)


class HealingColor(BaseSchema):
    """Healing color with effect description."""

    name: str
    hex: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    effect: str


class EmotionAnalyzeRequest(BaseSchema):
    """Emotion analysis request."""

    text: str = Field(..., min_length=1, max_length=2000)


class EmotionEntry(BaseSchema):
    """Individual emotion entry."""

    id: str
    date: datetime
    text: str
    emotions: EmotionState
    healing_colors: list[HealingColor] = Field(..., alias="healingColors")

    # RAG recommendation data
    rag_color_name: str | None = Field(None, alias="ragColorName")
    rag_psychological_effect: str | None = Field(None, alias="ragPsychologicalEffect")
    rag_recommendation_reason: str | None = Field(None, alias="ragRecommendationReason")
    rag_usage_method: str | None = Field(None, alias="ragUsageMethod")


class WeeklyStats(BaseSchema):
    """Weekly statistics."""

    active_days: int = Field(..., alias="activeDays")
    color_improvement: float = Field(..., alias="colorImprovement")
    mood_improvement: float = Field(..., alias="moodImprovement")
    stress_relief: float = Field(..., alias="stressRelief")


class WeeklyInsightResponse(BaseSchema):
    """Weekly insight response."""

    week_start: datetime = Field(..., alias="weekStart")
    week_end: datetime = Field(..., alias="weekEnd")
    emotion_distribution: EmotionState = Field(..., alias="emotionDistribution")
    improvement: str
    next_week_suggestion: str = Field(..., alias="nextWeekSuggestion")
    stats: WeeklyStats
