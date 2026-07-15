from fastapi import APIRouter

from backend.app.presentation.api.v1.events import event_router
from backend.app.presentation.api.v1.users import auth_router, user_router
from backend.app.presentation.api.v1.wishes import wish_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
v1_router.include_router(user_router, prefix="/users", tags=["users"])
v1_router.include_router(wish_router, prefix="/wishes", tags=["wishes"])
v1_router.include_router(event_router, prefix="/events", tags=["events"])
