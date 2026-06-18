import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.application.services.event_service import (
    EventMemberService,
    EventService,
)
from backend.app.domain.entities.event import EventCreate as EventCreateInput
from backend.app.domain.entities.event import EventUpdate as EventUpdateInput
from backend.app.domain.entities.user import User
from backend.app.domain.repositories.event_repository import (
    AbstractEventMemberRepository,
    AbstractEventRepository,
)
from backend.app.domain.repositories.user_repository import AbstractUserRepository
from backend.app.infrastructure.database.session import DbSession
from backend.app.infrastructure.repositories.event_repository import (
    SQLAlchemyEventMemberRepository,
    SQLAlchemyEventRepository,
)
from backend.app.infrastructure.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from backend.app.presentation.dependencies import get_current_user
from backend.app.presentation.schemas.event import (
    EventCreate,
    EventRead,
    EventUpdate,
)


def get_event_repo(session: DbSession) -> AbstractEventRepository:
    return SQLAlchemyEventRepository(session)


def get_event_member_repo(session: DbSession) -> AbstractEventMemberRepository:
    return SQLAlchemyEventMemberRepository(session)


def get_user_repo(session: DbSession) -> AbstractUserRepository:
    return SQLAlchemyUserRepository(session)


def get_event_service(
    event_repo: Annotated[AbstractEventRepository, Depends(get_event_repo)],
) -> EventService:
    return EventService(event_repo)


def get_event_member_service(
    event_repo: Annotated[AbstractEventRepository, Depends(get_event_repo)],
    event_member_repo: Annotated[
        AbstractEventMemberRepository, Depends(get_event_member_repo)
    ],
    user_repo: Annotated[AbstractUserRepository, Depends(get_user_repo)],
) -> EventMemberService:
    return EventMemberService(event_repo, event_member_repo, user_repo)


EventServiceDep = Annotated[EventService, Depends(get_event_service)]
EventMemberServiceDep = Annotated[EventMemberService, Depends(get_event_member_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]

event_router = APIRouter()


@event_router.post("", response_model=EventRead)
async def create_event(
    data: EventCreate,
    service: EventServiceDep,
    current_user: CurrentUser,
):
    return await service.create(
        current_user,
        EventCreateInput(
            title=data.title,
            price_limit=data.price_limit,
            status=data.status,
            description=data.description,
            image_url=str(data.image_url) if data.image_url else None,
        ),
    )


@event_router.get("/me", response_model=list[EventRead])
async def get_my_events(service: EventServiceDep, current_user: CurrentUser):
    return await service.get_list(current_user)


@event_router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: uuid.UUID,
    service: EventServiceDep,
    current_user: CurrentUser,
):
    return await service.get_by_id(event_id)


@event_router.put("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    service: EventServiceDep,
    current_user: CurrentUser,
):
    return await service.update(
        event_id,
        current_user,
        EventUpdateInput(
            title=data.title,
            price_limit=data.price_limit,
            status=data.status,
            description=data.description,
            image_url=str(data.image_url) if data.image_url else None,
        ),
    )


@event_router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: uuid.UUID,
    service: EventServiceDep,
    current_user: CurrentUser,
):
    await service.delete(event_id, current_user)


@event_router.post("/{event_id}/members", status_code=204)
async def add_member(
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    service: EventMemberServiceDep,
    current_user: CurrentUser,
):
    await service.add_member(current_user, user_id, event_id)


@event_router.delete("/{event_id}/members", status_code=204)
async def remove_member(
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    service: EventMemberServiceDep,
    current_user: CurrentUser,
):
    await service.remove_member(current_user, user_id, event_id)
