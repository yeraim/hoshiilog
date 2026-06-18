import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from backend.app.domain.entities.wish import Wish, WishType
from backend.app.domain.repositories.wish_repository import AbstractWishRepository
from backend.app.infrastructure.database.models import WishModel
from backend.app.infrastructure.database.session import DbSession


class SQLAlchemyWishRepository(AbstractWishRepository):
    def __init__(self, session: DbSession) -> None:
        self._session = session

    async def create(self, wish: Wish) -> Wish:
        model = WishModel.from_entity(wish)
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError:
            raise ValueError("Wish with this title already exists")
        return model.to_entity()

    async def get_by_id(self, wish_id: uuid.UUID) -> Wish | None:
        result = await self._session.execute(
            select(WishModel).where(WishModel.id == wish_id)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_list_by_user(self, user_id: uuid.UUID) -> list[Wish]:
        result = await self._session.execute(
            select(WishModel).where(WishModel.user_id == user_id)
        )
        return [m.to_entity() for m in result.scalars().all()]

    async def get_list_by_user_public(self, user_id: uuid.UUID) -> list[Wish]:
        result = await self._session.execute(
            select(WishModel).where(
                WishModel.user_id == user_id,
                WishModel.type == WishType.PUBLIC,
            )
        )
        return [m.to_entity() for m in result.scalars().all()]

    async def get_list_by_user_friends(self, user_id: uuid.UUID) -> list[Wish]:
        result = await self._session.execute(
            select(WishModel).where(
                WishModel.user_id == user_id,
                WishModel.type.in_([WishType.PUBLIC, WishType.FRIENDS_ONLY]),
            )
        )
        return [m.to_entity() for m in result.scalars().all()]

    async def update(self, wish: Wish) -> Wish:
        result = await self._session.execute(
            select(WishModel).where(WishModel.id == wish.id)
        )
        model = result.scalar_one()
        model.title = wish.title
        model.body = wish.body
        model.link = wish.link
        model.image_url = wish.image_url
        model.status = wish.status
        model.type = wish.type
        model.category = wish.category
        model.price = wish.price
        await self._session.flush()
        return model.to_entity()

    async def delete(self, wish_id: uuid.UUID) -> None:
        await self._session.execute(delete(WishModel).where(WishModel.id == wish_id))

    async def reserve(self, wish_id: uuid.UUID, reserver_id: uuid.UUID) -> Wish:
        result = await self._session.execute(
            select(WishModel).where(WishModel.id == wish_id)
        )
        model = result.scalar_one()
        model.reserved_by_id = reserver_id
        model.reserved_at = datetime.now(timezone.utc)
        await self._session.flush()
        return model.to_entity()

    async def cancel_reservation(self, wish_id: uuid.UUID) -> Wish:
        result = await self._session.execute(
            select(WishModel).where(WishModel.id == wish_id)
        )
        model = result.scalar_one()
        model.reserved_by_id = None
        model.reserved_at = None
        await self._session.flush()
        return model.to_entity()
