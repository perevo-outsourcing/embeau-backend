"""Dependency injection for FastAPI."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from embeau_api.core.security import verify_token
from embeau_api.db.session import get_db
from embeau_api.models import User
from embeau_api.services import (
    AuthService,
    ColorAnalyzerService,
    EmotionAnalyzerService,
    FeedbackService,
    RecommendationService,
    ReportService,
)


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    # Verify token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Get user from database
    auth_service = AuthService(db)
    try:
        user = await auth_service.get_user_by_id(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_optional_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get the current user if authenticated, or None."""
    if not authorization:
        return None

    try:
        return await get_current_user(authorization, db)
    except HTTPException:
        return None


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


# Service dependencies
def get_auth_service(db: DbSession) -> AuthService:
    """Get AuthService instance."""
    return AuthService(db)


def get_color_service(db: DbSession) -> ColorAnalyzerService:
    """Get ColorAnalyzerService instance."""
    return ColorAnalyzerService(db)


def get_emotion_service(db: DbSession) -> EmotionAnalyzerService:
    """Get EmotionAnalyzerService instance."""
    return EmotionAnalyzerService(db)


def get_recommendation_service(db: DbSession) -> RecommendationService:
    """Get RecommendationService instance."""
    return RecommendationService(db)


def get_feedback_service(db: DbSession) -> FeedbackService:
    """Get FeedbackService instance."""
    return FeedbackService(db)


def get_report_service(db: DbSession) -> ReportService:
    """Get ReportService instance."""
    return ReportService(db)


# Service type aliases
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ColorServiceDep = Annotated[ColorAnalyzerService, Depends(get_color_service)]
EmotionServiceDep = Annotated[EmotionAnalyzerService, Depends(get_emotion_service)]
RecommendationServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]
FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
