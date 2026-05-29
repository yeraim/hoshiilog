import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.models import User
from backend.app.events.schemas import EventCreate, EventRead, EventUpdate
from backend.app.events.services import EventMemberService, EventService

event_service = Annotated[EventService, Depends(EventService)]
eventmember_service = Annotated[EventMemberService, Depends(EventMemberService)]
current_user = Annotated[User, Depends(get_current_user)]

event_router = APIRouter()


@event_router.post("", response_model=EventRead)
async def create_event(
    event: EventCreate, service: event_service, current_user: current_user
):
    return await service.create(current_user, event)


@event_router.get("/me", response_model=list[EventRead])
async def get_my_events(service: event_service, current_user: current_user):
    return await service.get_list(current_user)


@event_router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: uuid.UUID, service: event_service, current_user: current_user
):
    return await service.get_by_id(event_id, current_user)


@event_router.put("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: uuid.UUID,
    event: EventUpdate,
    service: event_service,
    current_user: current_user,
):
    return await service.update(event_id, current_user, event)


@event_router.delete("/{event_id}", response_model=None)
async def delete_event(
    event_id: uuid.UUID, service: event_service, current_user: current_user
):
    await service.delete(event_id, current_user)


@event_router.post("/{event_id}/add_member", response_model=None)
async def add_member(
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    service: eventmember_service,
    current_user: current_user,
):
    return await service.add_member(current_user, user_id, event_id)


@event_router.post("/{event_id}/delete_member", response_model=None)
async def remove_member(
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    service: eventmember_service,
    current_user: current_user,
):
    await service.remove_member(current_user, user_id, event_id)
