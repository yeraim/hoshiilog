import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from backend.app.auth.models import User
from backend.app.base import BaseRepository
from backend.app.events.models import Event
from backend.app.events.schemas import EventCreate, EventUpdate


class EventRepository(BaseRepository):
    async def create(self, current_user: User, data: EventCreate):
        data_dict = data.model_dump()
        if data_dict.get("image_url"):
            data_dict["image_url"] = str(data_dict["image_url"])
        new_event = Event(**data_dict, user_id=current_user.id)
        self.session.add(new_event)

        try:
            await self.session.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=400, detail="Wish with this title already exists"
            )

        return new_event

    async def get_list(self, current_user: User):
        result = await self.session.execute(
            select(Event)
            .where(Event.user_id == current_user.id)
            .options(selectinload(Event.owner))
        )
        return result.scalars().all()

    async def get_by_id(self, event_id: uuid.UUID, current_user: User):
        return await self.get_or_404(Event, event_id, selectinload(Event.owner))

    async def update(self, event_to_change: Event, data: EventUpdate) -> Event:
        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("image_url"):
            update_data["image_url"] = str(update_data["image_url"])

        for key, value in update_data.items():
            setattr(event_to_change, key, value)

        await self.session.flush()
        return event_to_change

    async def delete(self, event: Event):
        return await self.session.delete(event)

    # async def reserve(self, wish: Wish, reserver: User):
    #     wish.reserver = reserver
    #     wish.reserved_at = datetime.now(timezone.utc)

    #     await self.session.flush()
    #     return wish

    # async def cancel_reservation(self, wish: Wish):
    #     wish.reserver = None
    #     wish.reserved_at = None

    #     await self.session.flush()
    #     return wish
