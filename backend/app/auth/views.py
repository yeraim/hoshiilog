import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.models import User
from backend.app.auth.schemas import (
    Token,
    UserChangePassword,
    UserCreate,
    UserRead,
)
from backend.app.auth.services import FollowService, UserService

user_service = Annotated[UserService, Depends(UserService)]
follow_service = Annotated[FollowService, Depends(FollowService)]
current_user = Annotated[User, Depends(get_current_user)]

auth_router = APIRouter()
user_router = APIRouter()


@auth_router.post("/register", response_model=UserRead)
async def register_user(user: UserCreate, service: user_service):
    """Endpoint to register a new user."""

    return await service.register_new_user(user.email, user.password)


@auth_router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: user_service
):
    """Endpoint to log in a user."""

    return await service.authenticate_user(form.username, form.password)


@auth_router.get("/me", response_model=UserRead)
async def me(user: current_user):
    """Endpoint to get current user."""
    return user


@user_router.get("", response_model=list[UserRead])
async def get_users(user: current_user, service: user_service):
    return await service.get_users()


@user_router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID, current_user: current_user, service: user_service
):
    return await service.get_user(user_id)


@user_router.post("/change_password", response_model=UserRead)
async def change_password(
    data: UserChangePassword, user: current_user, service: user_service
):
    return await service.change_password(user, data.old_password, data.new_password)


@user_router.post("/follow_user/{user_id}")
async def follow_user(user_id: uuid.UUID, user: current_user, service: follow_service):
    return await service.follow_user(user, user_id)


@user_router.post("/unfollow_user/{user_id}")
async def unfollow_user(
    user_id: uuid.UUID, user: current_user, service: follow_service
):
    return await service.unfollow_user(user, user_id)
