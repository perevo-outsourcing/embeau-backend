"""Recommendation API endpoints."""

from fastapi import APIRouter, Query

from embeau_api.deps import CurrentUser, RecommendationServiceDep
from embeau_api.schemas.base import ApiResponse
from embeau_api.schemas.recommendation import Recommendation

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", response_model=ApiResponse[Recommendation])
async def get_recommendations(
    current_user: CurrentUser,
    recommendation_service: RecommendationServiceDep,
) -> ApiResponse[Recommendation]:
    """
    Get personalized recommendations.

    Returns fashion items, food suggestions, and activities
    based on the user's personal color profile.
    """
    result = await recommendation_service.get_recommendations(current_user.id)
    return ApiResponse.ok(result)


@router.get("/by-color", response_model=ApiResponse[Recommendation])
async def get_recommendations_by_color(
    current_user: CurrentUser,
    recommendation_service: RecommendationServiceDep,
    color: str = Query(..., description="Hex color code (e.g., #E6E6FA)"),
) -> ApiResponse[Recommendation]:
    """
    Get recommendations for a specific healing color.

    Returns items that match the specified color for therapeutic purposes.
    """
    result = await recommendation_service.get_recommendations_by_color(
        current_user.id, color
    )
    return ApiResponse.ok(result)
