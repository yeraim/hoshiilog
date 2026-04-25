from typing import Sequence

from sqlalchemy import select

from backend.app.auth.models import User
from backend.app.database import DbSession


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, session: DbSession):
        self.session = session

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def create_user(self, email: str, password_hash: bytes) -> User:
        new_user = User(email=email, password=password_hash)
        self.session.add(new_user)
        await self.session.flush()
        return new_user

    async def get_users(self) -> Sequence[User]:
        result = await self.session.execute(select(User))
        return result.scalars().all()

    async def change_password(self, user: User, new_password: bytes) -> User:
        user.password = new_password
        await self.session.flush()
        return user

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, instance: User) -> None:
        await self.session.refresh(instance)
