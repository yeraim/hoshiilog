import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.application.services.wish_service import WishService
from backend.app.domain.entities.user import User
from backend.app.domain.entities.wish import WishCreate as WishCreateInput
from backend.app.domain.entities.wish import WishUpdate as WishUpdateInput
from backend.app.domain.repositories.user_repository import AbstractUserRepository
from backend.app.domain.repositories.wish_repository import AbstractWishRepository
from backend.app.infrastructure.database.session import DbSession
from backend.app.infrastructure.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from backend.app.infrastructure.repositories.wish_repository import (
    SQLAlchemyWishRepository,
)
from backend.app.presentation.dependencies import get_current_user
from backend.app.presentation.schemas.wish import (
    WishCreate,
    WishRead,
    WishReserveRead,
    WishUpdate,
)


def get_wish_repo(session: DbSession) -> AbstractWishRepository:
    return SQLAlchemyWishRepository(session)


def get_user_repo(session: DbSession) -> AbstractUserRepository:
    return SQLAlchemyUserRepository(session)


def get_wish_service(
    wish_repo: Annotated[AbstractWishRepository, Depends(get_wish_repo)],
    user_repo: Annotated[AbstractUserRepository, Depends(get_user_repo)],
) -> WishService:
    return WishService(wish_repo, user_repo)


WishServiceDep = Annotated[WishService, Depends(get_wish_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]

wish_router = APIRouter()


@wish_router.post("", response_model=WishRead)
async def create_wish(
    data: WishCreate,
    service: WishServiceDep,
    current_user: CurrentUser,
):
    return await service.create(
        current_user,
        WishCreateInput(
            title=data.title,
            price=data.price,
            status=data.status,
            type=data.type,
            category=data.category,
            body=data.body,
            link=str(data.link) if data.link else None,
            image_url=str(data.image_url) if data.image_url else None,
        ),
    )


@wish_router.get("/me", response_model=list[WishRead])
async def get_my_wishes(service: WishServiceDep, current_user: CurrentUser):
    return await service.get_list_by_user(current_user)


@wish_router.get("/user/{user_id}", response_model=list[WishReserveRead])
async def get_wishes_by_user(
    user_id: uuid.UUID,
    service: WishServiceDep,
    current_user: CurrentUser,
):
    return await service.get_list_by_user(current_user, user_id)


@wish_router.get("/{wish_id}", response_model=WishRead)
async def get_wish(
    wish_id: uuid.UUID,
    service: WishServiceDep,
    current_user: CurrentUser,
):
    return await service.get_by_id(wish_id, current_user)


@wish_router.put("/{wish_id}", response_model=WishRead)
async def update_wish(
    wish_id: uuid.UUID,
    data: WishUpdate,
    service: WishServiceDep,
    current_user: CurrentUser,
):
    return await service.update(
        wish_id,
        current_user,
        WishUpdateInput(
            title=data.title,
            price=data.price,
            status=data.status,
            type=data.type,
            category=data.category,
            body=data.body,
            link=str(data.link) if data.link else None,
            image_url=str(data.image_url) if data.image_url else None,
        ),
    )


@wish_router.delete("/{wish_id}", status_code=204)
async def delete_wish(
    wish_id: uuid.UUID,
    service: WishServiceDep,
    current_user: CurrentUser,
):
    await service.delete(wish_id, current_user)


@wish_router.post("/reserve_wish/{wish_id}", response_model=WishRead)
async def reserve_wish(
    wish_id: uuid.UUID,
    service: WishServiceDep,
    current_user: CurrentUser,
):
    return await service.reserve(wish_id, current_user)


@wish_router.post("/cancel_reservation/{wish_id}", response_model=WishRead)
async def cancel_reservation(
    wish_id: uuid.UUID,
    service: WishServiceDep,
    current_user: CurrentUser,
):
    return await service.cancel_reservation(wish_id, current_user)
