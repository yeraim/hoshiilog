import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select

from backend.app.auth.models import User
from backend.app.base import BaseRepository
from backend.app.wishes.models import Wish, WishType
from backend.app.wishes.schemas import WishCreate, WishUpdate


class WishRepository(BaseRepository):
    async def create(self, current_user: User, data: WishCreate) -> Wish:
        data_dict = data.model_dump()
        if data_dict.get("link"):
            data_dict["link"] = str(data_dict["link"])
        if data_dict.get("image_url"):
            data_dict["image_url"] = str(data_dict["image_url"])

        new_wish = Wish(**data_dict, user_id=current_user.id)
        self.session.add(new_wish)
        await self.session.flush()
        return new_wish

    async def get_by_user(self, user_id: uuid.UUID) -> Sequence[Wish]:
        result = await self.session.execute(select(Wish).where(Wish.user_id == user_id))
        return result.scalars().all()

    async def get_by_user_public(self, user_id: uuid.UUID) -> Sequence[Wish]:
        result = await self.session.execute(
            select(Wish).where(Wish.user_id == user_id, Wish.type == WishType.PUBLIC)
        )
        return result.scalars().all()

    async def get_by_user_friends(self, user_id: uuid.UUID) -> Sequence[Wish]:
        result = await self.session.execute(
            select(Wish).where(
                Wish.user_id == user_id, Wish.type == WishType.FRIENDS_ONLY
            )
        )
        return result.scalars().all()

    async def get_by_id(self, wish_id: uuid.UUID) -> Wish | None:
        result = await self.session.execute(select(Wish).where(Wish.id == wish_id))
        return result.scalars().first()

    async def update(self, wish_to_change: Wish, data: WishUpdate) -> Wish:
        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("link"):
            update_data["link"] = str(update_data["link"])
        if update_data.get("image_url"):
            update_data["image_url"] = str(update_data["image_url"])

        for key, value in update_data.items():
            setattr(wish_to_change, key, value)

        await self.session.flush()
        return wish_to_change

    async def delete(self, wish: Wish):
        return await self.session.delete(wish)

    async def reserve(self, wish: Wish, reserver: User):
        wish.reserver = reserver
        wish.reserved_at = datetime.now(timezone.utc)

        await self.session.flush()
        return wish

    async def cancel_reservation(self, wish: Wish):
        wish.reserver = None
        wish.reserved_at = None

        await self.session.flush()
        return wish
