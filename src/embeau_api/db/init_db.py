"""Database initialization and seed data."""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from embeau_api.core.security import hash_password
from embeau_api.db.session import AsyncSessionLocal, init_db
from embeau_api.models import User


async def create_test_user() -> None:
    """Create a test user for development."""
    async with AsyncSessionLocal() as session:
        # Check if test user exists
        result = await session.execute(
            select(User).where(User.email == "test@test.com")
        )
        existing = result.scalar_one_or_none()

        if not existing:
            test_user = User(
                email="test@test.com",
                participant_id="testtest",
                hashed_password=hash_password("testtest"),
                name="Test User",
                consent_given=True,
                consent_date=datetime.now(timezone.utc),
                is_active=True,
            )
            session.add(test_user)
            await session.commit()
            print("Test user created: test@test.com / testtest")
        else:
            print("Test user already exists")


async def main() -> None:
    """Initialize database and create seed data."""
    print("Initializing database...")
    await init_db()
    print("Database tables created")

    print("Creating test user...")
    await create_test_user()

    print("Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(main())
