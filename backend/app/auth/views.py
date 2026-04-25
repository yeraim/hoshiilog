from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.auth.schemas import UserCreate, UserRead
from backend.app.auth.services import UserService

user_service = Annotated[UserService, Depends(UserService)]

router = APIRouter()


@router.post("/register", response_model=UserRead)
async def register_user(user: UserCreate, service: user_service):
    """Endpoint to register a new user."""

    return await service.register_new_user(user.email, user.password)
