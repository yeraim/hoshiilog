from sqlalchemy import select

from backend.app.auth.models import User
from backend.app.database import DbSession


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, session: DbSession):
        self.session = session

    async def get_user_by_email(self, email: str) -> User | None:
        """Fetch a user by their email."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def create_user(self, email: str, password_hash: bytes) -> User:
        """Create a new user with the given email and password hash."""
        new_user = User(email=email, password=password_hash)
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user
