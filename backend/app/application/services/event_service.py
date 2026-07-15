import uuid

from backend.app.domain.entities.event import (
    Event,
    EventCreate,
    EventMember,
    EventUpdate,
)
from backend.app.domain.entities.user import User
from backend.app.domain.repositories.event_repository import (
    AbstractEventMemberRepository,
    AbstractEventRepository,
)
from backend.app.domain.repositories.user_repository import AbstractUserRepository
from backend.app.exceptions import ConflictError, NotFoundError, PermissionDeniedError


class EventService:
    def __init__(self, event_repo: AbstractEventRepository) -> None:
        self._event_repo = event_repo

    # TODO: do something about this
    def _assert_owner(self, event: Event, current_user: User) -> None:
        if event.user_id != current_user.id:
            raise PermissionDeniedError(
                "You don't have permission to modify this event"
            )

    async def create(self, current_user: User, data: EventCreate) -> Event:
        event = Event(
            user_id=current_user.id,
            title=data.title,
            price_limit=data.price_limit,
            description=data.description,
            image_url=data.image_url,
            status=data.status,
        )
        return await self._event_repo.create(event)

    async def get_by_id(self, event_id: uuid.UUID) -> Event:
        event = await self._event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event not found")
        return event

    async def get_list(self, current_user: User) -> list[Event]:
        return await self._event_repo.get_list(current_user.id)

    async def update(
        self, event_id: uuid.UUID, current_user: User, data: EventUpdate
    ) -> Event:
        event = await self.get_by_id(event_id)
        self._assert_owner(event, current_user)

        if data.title is not None:
            event.title = data.title
        if data.description is not None:
            event.description = data.description
        if data.image_url is not None:
            event.image_url = data.image_url
        if data.status is not None:
            event.status = data.status
        if data.price_limit is not None:
            event.price_limit = data.price_limit

        return await self._event_repo.update(event)

    async def delete(self, event_id: uuid.UUID, current_user: User) -> None:
        event = await self.get_by_id(event_id)
        self._assert_owner(event, current_user)
        await self._event_repo.delete(event_id)


class EventMemberService:
    def __init__(
        self,
        event_repo: AbstractEventRepository,
        event_member_repo: AbstractEventMemberRepository,
        user_repo: AbstractUserRepository,
    ) -> None:
        self._event_repo = event_repo
        self._event_member_repo = event_member_repo
        self._user_repo = user_repo

    async def add_member(
        self, current_user: User, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> EventMember:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        event = await self._event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event not found")

        if event.user_id != current_user.id:
            raise PermissionDeniedError(
                "You don't have permission to modify this event"
            )

        return await self._event_member_repo.add_member(user_id, event_id)

    async def remove_member(
        self, current_user: User, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        event = await self._event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event not found")

        if event.user_id != current_user.id:
            raise PermissionDeniedError(
                "You don't have permission to modify this event"
            )

        event_member = await self._event_member_repo.get_member(user_id, event_id)
        if not event_member:
            raise ConflictError("User is not present in the event")

        await self._event_member_repo.remove_member(user_id, event_id)

    async def assign_gift_targets(self): ...
