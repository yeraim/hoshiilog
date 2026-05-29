import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status

from backend.app.auth.models import User
from backend.app.auth.repositories import UserRepository
from backend.app.events.repositories import EventMemberRepository, EventRepository
from backend.app.events.schemas import EventCreate, EventUpdate

event_repo = Annotated[EventRepository, Depends(EventRepository)]
eventmember_repo = Annotated[EventMemberRepository, Depends(EventMemberRepository)]
user_repo = Annotated[UserRepository, Depends(UserRepository)]


class EventService:
    def __init__(self, event_repo: event_repo):
        self.event_repo = event_repo

    async def create(self, current_user: User, data: EventCreate):
        event = await self.event_repo.create(current_user, data)
        await self.event_repo.commit()
        await self.event_repo.refresh(event)
        return event

    async def get_by_id(self, event_id: uuid.UUID):
        return await self.event_repo.get_by_id(event_id)

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


class EventMemberService:
    def __init__(
        self,
        eventmember_repo: eventmember_repo,
        user_repo: user_repo,
        event_repo: event_repo,
    ):
        self.eventmember_repo = eventmember_repo
        self.user_repo = user_repo
        self.event_repo = event_repo

    async def add_member(
        self, current_user: User, user_id: uuid.UUID, event_id: uuid.UUID
    ):
        # check on service side if can add (admin/owner priviligies +
        # event already locked)
        user = await self.user_repo.get_user_by_id(user_id)
        event = await self.event_repo.get_by_id(event_id)

        await self.event_repo.assert_owner(event, current_user)

        # still thinking about implementing this and if it is
        # even needed (same goes for removing member)
        # if event.status != EventStatus.PLANNING:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="You can't add members outside of planning mode",
        #     )
        event_member = await self.eventmember_repo.add_member(user, event)
        await self.eventmember_repo.commit()
        await self.eventmember_repo.refresh(event_member)
        return event_member

    async def remove_member(
        self, current_user: User, user_id: uuid.UUID, event_id: uuid.UUID
    ):
        event = await self.event_repo.get_by_id(event_id)
        await self.event_repo.assert_owner(event, current_user)

        event_member = await self.eventmember_repo.get_member(user_id, event_id)
        if not event_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not present in the event",
            )

        await self.eventmember_repo.remove_member(event_member)
        await self.eventmember_repo.commit()

    async def assign_gift_targets(): ...
