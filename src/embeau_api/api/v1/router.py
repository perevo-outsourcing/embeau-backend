"""API v1 router - combines all endpoint routers."""

from fastapi import APIRouter

from embeau_api.api.v1.auth import router as auth_router
from embeau_api.api.v1.color import router as color_router
from embeau_api.api.v1.emotion import router as emotion_router
from embeau_api.api.v1.feedback import router as feedback_router
from embeau_api.api.v1.recommendation import router as recommendation_router
from embeau_api.api.v1.report import router as report_router

router = APIRouter()

# Include all routers
router.include_router(auth_router)
router.include_router(color_router)
router.include_router(emotion_router)
router.include_router(recommendation_router)
router.include_router(feedback_router)
router.include_router(report_router)
