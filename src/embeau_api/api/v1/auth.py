"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, status

from embeau_api.core.exceptions import AuthenticationError, ValidationError
from embeau_api.deps import AuthServiceDep, CurrentUser
from embeau_api.schemas.auth import LoginRequest, LoginResponse, UserResponse
from embeau_api.schemas.base import ApiResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login(
    data: LoginRequest,
    auth_service: AuthServiceDep,
) -> ApiResponse[LoginResponse]:
    """
    Login with email and participant ID.

    For research participants, the participant ID serves as authentication.
    """
    try:
        user, token = await auth_service.login(data)
        user_response = auth_service.to_response(user)

        return ApiResponse.ok(
            LoginResponse(user=user_response, token=token)
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> ApiResponse[None]:
    """Logout the current user."""
    await auth_service.logout(current_user.id)
    return ApiResponse.ok(None)


@router.get("/profile", response_model=ApiResponse[UserResponse])
async def get_profile(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> ApiResponse[UserResponse]:
    """Get the current user's profile."""
    return ApiResponse.ok(auth_service.to_response(current_user))
