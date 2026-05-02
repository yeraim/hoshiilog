import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.auth.models import Follow, User
from backend.app.database import Base, DbSession


class BaseRepository:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, instance: Base) -> None:
        await self.session.refresh(instance)


class UserRepository(BaseRepository):
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

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.following_relationships).selectinload(
                    Follow.followed_user
                ),
                selectinload(User.follower_relationships).selectinload(
                    Follow.following_user
                ),
            )
        )
        return result.scalars().first()

    async def change_password(self, user: User, new_password: bytes) -> User:
        user.password = new_password
        await self.session.flush()
        return user


class FollowRepository(BaseRepository):
    async def follow_user(self, following_user: User, followed_user: User) -> Follow:
        new_follow = Follow(following_user=following_user, followed_user=followed_user)
        self.session.add(new_follow)
        await self.session.flush()
        return new_follow

    async def unfollow_user(self, following_user: User, followed_user: User):
        result = await self.session.execute(
            select(Follow).where(
                Follow.following_user_id == following_user.id,
                Follow.followed_user_id == followed_user.id,
            )
        )
        follow_for_deletion = result.scalar_one_or_none()
        if follow_for_deletion:
            await self.session.delete(follow_for_deletion)

    async def check_followers(
        self, following_user: User, followed_user: User
    ) -> bool | None:
        result = await self.session.execute(
            select(
                select(Follow)
                .where(
                    Follow.following_user_id == following_user.id,
                    Follow.followed_user_id == followed_user.id,
                )
                .exists()
            )
        )
        return result.scalar()
