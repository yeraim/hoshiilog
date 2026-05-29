import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from backend.app.auth.models import User
from backend.app.base import BaseRepository
from backend.app.events.models import Event, EventMember
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
            await self.session.rollback()
            raise HTTPException(
                status_code=400, detail="Event with this title already exists"
            )

        return new_event

    async def get_list(self, current_user: User):
        result = await self.session.execute(
            select(Event)
            .where(Event.user_id == current_user.id)
            .options(selectinload(Event.owner))
        )
        return result.scalars().all()

    async def get_by_id(self, event_id: uuid.UUID) -> Event:
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


class EventMemberRepository(BaseRepository):
    async def get_member(
        self, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> EventMember | None:
        result = await self.session.execute(
            select(EventMember).where(
                EventMember.user_id == user_id, EventMember.event_id == event_id
            )
        )
        return result.scalars().first()

    async def add_member(self, user: User, event: Event):
        new_member = EventMember(event_id=event.id, user_id=user.id)
        self.session.add(new_member)

        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail="User is already a member")

        return new_member

    async def remove_member(self, event_member: EventMember):
        return await self.session.delete(event_member)

    async def assign_gift_targets():
        pass
