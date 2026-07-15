import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from backend.app.domain.entities.user import Follow, User
from backend.app.domain.repositories.user_repository import (
    AbstractFollowRepository,
    AbstractUserRepository,
)
from backend.app.infrastructure.database.models import FollowModel, UserModel
from backend.app.infrastructure.database.session import DbSession


class SQLAlchemyUserRepository(AbstractUserRepository):
    """Repository for user-related database operations."""

    def __init__(self, session: DbSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(
                selectinload(UserModel.following_relationships).selectinload(
                    FollowModel.followed_user
                ),
                selectinload(UserModel.follower_relationships).selectinload(
                    FollowModel.following_user
                ),
            )
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_list(self) -> list[User]:
        result = await self._session.execute(select(UserModel))
        return [m.to_entity() for m in result.scalars().all()]

    async def create(self, user: User) -> User:
        model = UserModel.from_entity(user)
        self._session.add(model)
        await self._session.flush()
        return model.to_entity()

    async def delete(self, user_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            delete(UserModel).where(UserModel.id == user_id)
        )
        return result.rowcount > 0

    async def change_password(self, user_id: uuid.UUID, new_password: bytes) -> User:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one()
        model.password = new_password
        await self._session.flush()
        return model.to_entity()

    async def are_friends(self, user1_id: uuid.UUID, user2_id: uuid.UUID) -> bool:
        user1_follows_user2 = (
            select(FollowModel)
            .where(
                FollowModel.following_user_id == user1_id,
                FollowModel.followed_user_id == user2_id,
            )
            .exists()
        )
        user2_follows_user1 = (
            select(FollowModel)
            .where(
                FollowModel.following_user_id == user2_id,
                FollowModel.followed_user_id == user1_id,
            )
            .exists()
        )
        result = await self._session.execute(
            select(user1_follows_user2, user2_follows_user1)
        )
        a, b = result.one()
        return a and b


class FollowRepository(AbstractFollowRepository):
    def __init__(self, session: DbSession) -> None:
        self._session = session

    async def follow_user(
        self, following_user_id: uuid.UUID, followed_user_id: uuid.UUID
    ) -> Follow:
        obj = FollowModel(
            following_user_id=following_user_id,
            followed_user_id=followed_user_id,
        )
        self._session.add(obj)
        await self._session.flush()
        return obj.to_entity()

    async def unfollow_user(
        self, following_user_id: uuid.UUID, followed_user_id: uuid.UUID
    ) -> None:
        await self._session.execute(
            delete(FollowModel).where(
                FollowModel.following_user_id == following_user_id,
                FollowModel.followed_user_id == followed_user_id,
            )
        )

    async def check_followers(
        self, following_user_id: uuid.UUID, followed_user_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(
                select(FollowModel)
                .where(
                    FollowModel.following_user_id == following_user_id,
                    FollowModel.followed_user_id == followed_user_id,
                )
                .exists()
            )
        )
        return result.scalar()
