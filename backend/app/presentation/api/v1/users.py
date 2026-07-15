import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from backend.app.application.services.user_service import FollowService, UserService
from backend.app.domain.entities.user import User
from backend.app.domain.repositories.user_repository import (
    AbstractFollowRepository,
    AbstractUserRepository,
)
from backend.app.infrastructure.database.session import DbSession
from backend.app.infrastructure.repositories.user_repository import (
    FollowRepository,
)
from backend.app.presentation.dependencies import get_current_user, get_user_repo
from backend.app.presentation.schemas.user import (
    DetailedUserRead,
    Token,
    UserChangePassword,
    UserCreate,
    UserRead,
)


def get_follow_repo(session: DbSession) -> AbstractFollowRepository:
    return FollowRepository(session)


def get_user_service(
    repo: Annotated[AbstractUserRepository, Depends(get_user_repo)],
) -> UserService:
    return UserService(repo)


def get_follow_service(
    follow_repo: Annotated[AbstractFollowRepository, Depends(get_follow_repo)],
    user_repo: Annotated[AbstractUserRepository, Depends(get_user_repo)],
) -> FollowService:
    return FollowService(follow_repo, user_repo)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
FollowServiceDep = Annotated[FollowService, Depends(get_follow_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]

auth_router = APIRouter()
user_router = APIRouter()


@auth_router.post("/register", response_model=UserRead)
async def register(data: UserCreate, service: UserServiceDep):
    return await service.register(data.email, data.name, data.password)


@auth_router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: UserServiceDep,
):
    return await service.login(form.username, form.password)


@auth_router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser):
    return current_user


@user_router.get("", response_model=list[UserRead])
async def list_users(current_user: CurrentUser, service: UserServiceDep):
    return await service.list_users()


@user_router.get("/{user_id}", response_model=DetailedUserRead)
async def get_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    service: UserServiceDep,
):
    return await service.get_user(user_id)


@user_router.post("/change_password", response_model=UserRead)
async def change_password(
    data: UserChangePassword,
    current_user: CurrentUser,
    service: UserServiceDep,
):
    return await service.change_password(
        current_user, data.old_password, data.new_password
    )


@user_router.post("/follow/{user_id}", status_code=204)
async def follow_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    service: FollowServiceDep,
):
    await service.follow_user(current_user, user_id)


@user_router.post("/unfollow/{user_id}", status_code=204)
async def unfollow_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    service: FollowServiceDep,
):
    await service.unfollow_user(current_user, user_id)
