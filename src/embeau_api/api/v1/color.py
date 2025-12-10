"""Color analysis API endpoints."""

from fastapi import APIRouter, HTTPException, status

from embeau_api.core.exceptions import ColorAnalysisError, NotFoundError
from embeau_api.deps import ColorServiceDep, CurrentUser
from embeau_api.schemas.base import ApiResponse
from embeau_api.schemas.color import (
    ColorAnalyzeRequest,
    DailyHealingColorResponse,
    PersonalColorResult,
)

router = APIRouter(prefix="/color", tags=["Color Analysis"])


@router.post("/analyze", response_model=ApiResponse[PersonalColorResult])
async def analyze_color(
    data: ColorAnalyzeRequest,
    current_user: CurrentUser,
    color_service: ColorServiceDep,
) -> ApiResponse[PersonalColorResult]:
    """
    Analyze a face image to determine personal color.

    Accepts a base64-encoded image and returns personal color analysis
    including season, tone, and recommended colors.
    """
    try:
        result = await color_service.analyze_image(current_user.id, data.image)
        return ApiResponse.ok(result)
    except ColorAnalysisError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )


@router.get("/result", response_model=ApiResponse[PersonalColorResult])
async def get_color_result(
    current_user: CurrentUser,
    color_service: ColorServiceDep,
) -> ApiResponse[PersonalColorResult]:
    """Get the user's stored personal color analysis result."""
    try:
        result = await color_service.get_color_result(current_user.id)
        return ApiResponse.ok(result)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No color analysis result found. Please complete a color analysis first.",
        )


@router.get("/daily-healing", response_model=ApiResponse[DailyHealingColorResponse])
async def get_daily_healing_color(
    current_user: CurrentUser,
    color_service: ColorServiceDep,
) -> ApiResponse[DailyHealingColorResponse]:
    """
    Get today's healing color recommendation.

    Returns a personalized healing color based on the user's
    personal color profile and current emotional state.
    """
    result = await color_service.get_daily_healing_color(current_user.id)
    return ApiResponse.ok(result)
