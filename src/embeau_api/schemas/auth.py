"""Authentication schemas."""

from datetime import datetime

from pydantic import EmailStr, Field

from embeau_api.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    """Login request schema."""

    email: EmailStr
    participant_id: str = Field(..., min_length=1, max_length=50, alias="participantId")


class RegisterRequest(BaseSchema):
    """Registration request schema."""

    email: EmailStr
    participant_id: str = Field(..., min_length=1, max_length=50, alias="participantId")
    password: str = Field(..., min_length=6, max_length=100)
    name: str | None = Field(None, max_length=100)
    consent_given: bool = Field(False, alias="consentGiven")


class TokenResponse(BaseSchema):
    """Token response schema."""

    access_token: str = Field(..., alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    expires_in: int = Field(..., alias="expiresIn")


class UserResponse(BaseSchema):
    """User response schema."""

    id: str
    email: str
    participant_id: str = Field(..., alias="participantId")
    name: str | None = None
    personal_color: "PersonalColorSummary | None" = Field(None, alias="personalColor")
    created_at: datetime = Field(..., alias="createdAt")


class PersonalColorSummary(BaseSchema):
    """Summary of personal color for user profile."""

    season: str
    tone: str


class LoginResponse(BaseSchema):
    """Full login response."""

    user: UserResponse
    token: TokenResponse


# Update forward reference
UserResponse.model_rebuild()
