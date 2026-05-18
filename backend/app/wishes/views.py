import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.models import User
from backend.app.wishes.schemas import WishCreate, WishRead, WishUpdate
from backend.app.wishes.services import WishService

wish_service = Annotated[WishService, Depends(WishService)]
current_user = Annotated[User, Depends(get_current_user)]

wish_router = APIRouter()


@wish_router.post("", response_model=WishRead)
async def create_wish(
    wish: WishCreate, service: wish_service, current_user: current_user
):
    return await service.create(current_user, wish)


@wish_router.get("/me", response_model=list[WishRead])
async def get_my_wishes(service: wish_service, current_user: current_user):
    return await service.get_by_user(current_user)


@wish_router.get("/user/{user_id}", response_model=list[WishRead])
async def get_wishes(
    user_id: uuid.UUID, service: wish_service, current_user: current_user
):
    return await service.get_by_user(current_user, user_id)


@wish_router.get("/{wish_id}", response_model=WishRead)
async def get_wish(
    wish_id: uuid.UUID, service: wish_service, current_user: current_user
):
    return await service.get_by_id(wish_id)


@wish_router.put("/{wish_id}", response_model=WishRead)
async def update_wish(
    wish_id: uuid.UUID,
    wish: WishUpdate,
    service: wish_service,
    current_user: current_user,
):
    return await service.update(wish_id, current_user, wish)


@wish_router.delete("/{wish_id}", response_model=None)
async def delete_wish(
    wish_id: uuid.UUID, service: wish_service, current_user: current_user
):
    await service.delete(wish_id, current_user)


@wish_router.post("/reserve_wish/{wish_id}", response_model=WishRead)
async def reserve_wish(
    wish_id: uuid.UUID, service: wish_service, current_user: current_user
):
    return await service.reserve(wish_id, current_user)


@wish_router.post("/cancel_reservation/{wish_id}", response_model=WishRead)
async def cancel_reservation(
    wish_id: uuid.UUID, service: wish_service, current_user: current_user
):
    return await service.cancel_reservation(wish_id, current_user)
