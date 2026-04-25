from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.app.auth.views import router as auth_router


class ErrorMessage(BaseModel):
    """Represents a single error message."""

    msg: str


class ErrorResponse(BaseModel):
    """Defines the structure for API error responses."""

    detail: list[ErrorMessage] | None = None


api_router = APIRouter(
    default_response_class=JSONResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


@api_router.get("/healthcheck", include_in_schema=False)
def healthcheck():
    """Simple healthcheck endpoint."""
    return {"status": "ok"}


api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
