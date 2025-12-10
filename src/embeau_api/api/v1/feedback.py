"""Feedback API endpoints."""

from fastapi import APIRouter

from embeau_api.deps import CurrentUser, FeedbackServiceDep
from embeau_api.schemas.base import ApiResponse
from embeau_api.schemas.feedback import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=ApiResponse[FeedbackResponse])
async def submit_feedback(
    data: FeedbackRequest,
    current_user: CurrentUser,
    feedback_service: FeedbackServiceDep,
) -> ApiResponse[FeedbackResponse]:
    """
    Submit user feedback.

    Allows users to rate their experience with color analysis,
    emotion mapping, healing colors, or recommendations.
    This data is used for research purposes.
    """
    result = await feedback_service.submit_feedback(current_user.id, data)
    return ApiResponse.ok(result)
