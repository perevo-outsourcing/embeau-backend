"""Authentication service."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from embeau_api.config import get_settings
from embeau_api.core.exceptions import AuthenticationError, NotFoundError, ValidationError
from embeau_api.core.logging import ActionType, research_logger
from embeau_api.core.security import create_access_token, hash_password, verify_password
from embeau_api.models import User, UserSession
from embeau_api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

settings = get_settings()


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, data: RegisterRequest) -> User:
        """Register a new research participant."""
        # Check if email already exists
        existing = await self.db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise ValidationError("Email already registered", field="email")

        # Check if participant_id already exists
        existing = await self.db.execute(
            select(User).where(User.participant_id == data.participant_id)
        )
        if existing.scalar_one_or_none():
            raise ValidationError("Participant ID already registered", field="participantId")

        # Create user
        user = User(
            email=data.email,
            participant_id=data.participant_id,
            hashed_password=hash_password(data.password),
            name=data.name,
            consent_given=data.consent_given,
            consent_date=datetime.now(timezone.utc) if data.consent_given else None,
        )
        self.db.add(user)
        await self.db.flush()

        research_logger.log(
            action_type=ActionType.LOGIN,
            user_id=user.id,
            action_data={"type": "registration"},
        )

        return user

    async def login(self, data: LoginRequest) -> tuple[User, TokenResponse]:
        """Authenticate a user and return tokens."""
        # Find user by email
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("Invalid email or participant ID")

        # Verify participant_id (used as password alternative for research)
        if user.participant_id != data.participant_id:
            raise AuthenticationError("Invalid email or participant ID")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Create access token
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email}
        )

        # Create session record
        session = UserSession(
            user_id=user.id,
            token_hash=hash_password(access_token[:50]),  # Hash part of token for lookup
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.access_token_expire_minutes),
        )
        self.db.add(session)

        research_logger.log(
            action_type=ActionType.LOGIN,
            user_id=user.id,
            session_id=session.id,
            action_data={"type": "login"},
        )

        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

        return user, token_response

    async def get_user_by_id(self, user_id: str) -> User:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User", user_id)

        return user

    async def logout(self, user_id: str, session_id: str | None = None) -> None:
        """Log out a user."""
        if session_id:
            result = await self.db.execute(
                select(UserSession).where(
                    UserSession.id == session_id, UserSession.user_id == user_id
                )
            )
            session = result.scalar_one_or_none()
            if session:
                session.ended_at = datetime.now(timezone.utc)

        research_logger.log(
            action_type=ActionType.LOGOUT,
            user_id=user_id,
            session_id=session_id,
            action_data={"type": "logout"},
        )

    def to_response(self, user: User) -> UserResponse:
        """Convert User model to response schema."""
        personal_color = None
        if user.color_result:
            from embeau_api.schemas.auth import PersonalColorSummary

            personal_color = PersonalColorSummary(
                season=user.color_result.season,
                tone=user.color_result.tone,
            )

        return UserResponse(
            id=user.id,
            email=user.email,
            participant_id=user.participant_id,
            name=user.name,
            personal_color=personal_color,
            created_at=user.created_at,
        )
