"""Emotion analysis API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from embeau_api.core.exceptions import EmotionAnalysisError
from embeau_api.deps import CurrentUser, EmotionServiceDep
from embeau_api.schemas.base import ApiResponse
from embeau_api.schemas.emotion import (
    EmotionAnalyzeRequest,
    EmotionEntry,
    WeeklyInsightResponse,
)

router = APIRouter(prefix="/emotion", tags=["Emotion Analysis"])


@router.post("/analyze", response_model=ApiResponse[EmotionEntry])
async def analyze_emotion(
    data: EmotionAnalyzeRequest,
    current_user: CurrentUser,
    emotion_service: EmotionServiceDep,
) -> ApiResponse[EmotionEntry]:
    """
    Analyze emotion from text input.

    Takes user's description of their feelings and returns
    emotion scores along with healing color recommendations.
    """
    try:
        result = await emotion_service.analyze_emotion(current_user.id, data.text)
        return ApiResponse.ok(result)
    except EmotionAnalysisError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )


@router.get("/history", response_model=ApiResponse[list[EmotionEntry]])
async def get_emotion_history(
    current_user: CurrentUser,
    emotion_service: EmotionServiceDep,
    limit: int = Query(default=30, ge=1, le=100, description="Number of entries to return"),
) -> ApiResponse[list[EmotionEntry]]:
    """
    Get the user's emotion history.

    Returns a list of past emotion entries sorted by date (newest first).
    """
    entries = await emotion_service.get_emotion_history(current_user.id, limit)
    return ApiResponse.ok(entries)


@router.get("/weekly-insight", response_model=ApiResponse[WeeklyInsightResponse])
async def get_weekly_insight(
    current_user: CurrentUser,
    emotion_service: EmotionServiceDep,
) -> ApiResponse[WeeklyInsightResponse]:
    """
    Get weekly emotion insight and statistics.

    Returns aggregated emotion data, improvement insights,
    and suggestions for the upcoming week.
    """
    insight = await emotion_service.get_weekly_insight(current_user.id)
    return ApiResponse.ok(insight)
