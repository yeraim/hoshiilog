import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from backend.app.domain.entities.event import Event, EventMember
from backend.app.domain.repositories.event_repository import (
    AbstractEventMemberRepository,
    AbstractEventRepository,
)
from backend.app.infrastructure.database.models import EventMemberModel, EventModel
from backend.app.infrastructure.database.session import DbSession


class SQLAlchemyEventRepository(AbstractEventRepository):
    def __init__(self, session: DbSession) -> None:
        self._session = session

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        result = await self._session.execute(
            select(EventModel).where(EventModel.id == event_id)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_list(self, user_id: uuid.UUID) -> list[Event]:
        result = await self._session.execute(
            select(EventModel).where(EventModel.user_id == user_id)
        )
        return [m.to_entity() for m in result.scalars().all()]

    async def create(self, event: Event) -> Event:
        model = EventModel.from_entity(event)
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError:
            raise ValueError("Event with this title already exists")
        return model.to_entity()

    async def update(self, event: Event) -> Event:
        result = await self._session.execute(
            select(EventModel).where(EventModel.id == event.id)
        )
        model = result.scalar_one()
        model.title = event.title
        model.description = event.description
        model.image_url = event.image_url
        model.status = event.status
        model.price_limit = event.price_limit
        await self._session.flush()
        return model.to_entity()

    async def delete(self, event_id: uuid.UUID) -> None:
        await self._session.execute(delete(EventModel).where(EventModel.id == event_id))


class SQLAlchemyEventMemberRepository(AbstractEventMemberRepository):
    def __init__(self, session: DbSession) -> None:
        self._session = session

    async def get_member(
        self, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> EventMember | None:
        result = await self._session.execute(
            select(EventMemberModel).where(
                EventMemberModel.user_id == user_id,
                EventMemberModel.event_id == event_id,
            )
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def add_member(self, user_id: uuid.UUID, event_id: uuid.UUID) -> EventMember:
        model = EventMemberModel(user_id=user_id, event_id=event_id)
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError:
            raise ValueError("User is already a member of this event")
        return model.to_entity()

    async def remove_member(self, user_id: uuid.UUID, event_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(EventMemberModel).where(
                EventMemberModel.user_id == user_id,
                EventMemberModel.event_id == event_id,
            )
        )
