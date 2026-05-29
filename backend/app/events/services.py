import uuid
from typing import Annotated

from fastapi import Depends

from backend.app.auth.models import User
from backend.app.events.repositories import EventRepository
from backend.app.events.schemas import EventCreate, EventUpdate

event_repo = Annotated[EventRepository, Depends(EventRepository)]


class EventService:
    def __init__(self, event_repo: event_repo):
        self.event_repo = event_repo

    async def create(self, current_user: User, data: EventCreate):
        event = await self.event_repo.create(current_user, data)
        await self.event_repo.commit()
        await self.event_repo.refresh(event)
        return event

    async def get_by_id(self, event_id: uuid.UUID, current_user: User):
        return await self.event_repo.get_by_id(event_id, current_user)

    async def get_list(self, current_user: User):
        return await self.event_repo.get_list(current_user)

    async def update(self, event_id: uuid.UUID, current_user: User, data: EventUpdate):
        event = await self.event_repo.get_by_id(event_id, current_user)
        await self.event_repo.assert_owner(event, current_user)
        event = await self.event_repo.update(event, data)
        await self.event_repo.commit()
        await self.event_repo.refresh(event)
        return event

    async def delete(self, event_id: uuid.UUID, current_user: User):
        event = await self.event_repo.get_by_id(event_id, current_user)
        await self.event_repo.assert_owner(event, current_user)
        await self.event_repo.delete(event)
        await self.event_repo.commit()
