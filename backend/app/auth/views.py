from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.models import User
from backend.app.auth.schemas import Token, UserCreate, UserRead
from backend.app.auth.services import UserService

user_service = Annotated[UserService, Depends(UserService)]
current_user = Annotated[User, Depends(get_current_user)]

router = APIRouter()


@router.post("/register", response_model=UserRead)
async def register_user(user: UserCreate, service: user_service):
    """Endpoint to register a new user."""

    return await service.register_new_user(user.email, user.password)


@router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: user_service
):
    """Endpoint to log in a user."""

    return await service.authenticate_user(form.username, form.password)


@router.get("/me", response_model=UserRead)
async def me(user: current_user):
    """Endpoint to get current user."""
    return user
