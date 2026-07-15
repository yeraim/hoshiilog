import logging
from contextlib import asynccontextmanager

import sentry_sdk
from arq import create_pool
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.app.api import api_router
from backend.app.config import app_configs, settings
from backend.app.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from backend.app.infrastructure.database.session import engine
from backend.app.infrastructure.redis import arq_redis_settings
from backend.app.logging import configure_logging

log = logging.getLogger(__name__)
configure_logging()


async def not_found(request: Request, _exc: HTTPException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": [{"msg": "Not Found."}]},
    )


async def domain_not_found(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail},
    )


async def domain_permission_denied(request: Request, exc: PermissionDeniedError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.detail},
    )


async def domain_conflict(request: Request, exc: ConflictError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.detail},
    )


async def domain_authentication_error(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


exception_handlers = {
    404: not_found,
    NotFoundError: domain_not_found,
    PermissionDeniedError: domain_permission_denied,
    ConflictError: domain_conflict,
    AuthenticationError: domain_authentication_error,
}


async def check_db_connection():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            log.info("Database connection successful.")
    except Exception as e:
        log.error(f"Database connection failed: {e}")
        raise e


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # Run DB health check
    await check_db_connection()

    # arq pool for enqueuing crawl jobs (workers run in a separate process).
    # Reuses the project's REDIS_URL — no second Redis config.
    app.state.arq_pool = await create_pool(arq_redis_settings())
    log.info("arq pool ready")

    yield

    # --- Shutdown ---
    # Clean up resources, close connections, etc.
    await app.state.arq_pool.aclose()
    await engine.dispose()


if settings.ENVIRONMENT.is_deployed:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
    )


app = FastAPI(**app_configs, lifespan=lifespan, exception_handlers=exception_handlers)

app.include_router(api_router, prefix="/api")


# # package backend and frontend together, and serve the frontend from the backend
# # we create the ASGI for the app
# app = FastAPI(exception_handlers=exception_handlers, openapi_url="")
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# app.add_middleware(GZipMiddleware, minimum_size=1000)

# # we create the ASGI for the frontend
# frontend = FastAPI(openapi_url="")
# frontend.add_middleware(GZipMiddleware, minimum_size=1000)


# @frontend.middleware("http")
# async def default_page(request, call_next):
#     response = await call_next(request)
#     if response.status_code == 404:
#         if STATIC_DIR:
#             return FileResponse(path.join(STATIC_DIR, "index.html"))
#     return response


# # we create the Web API framework
# api = FastAPI(
#     title="Dispatch",
#     description="Welcome to Dispatch's API documentation! Here you will able to discover all of the ways you can interact with the Dispatch API.",  # noqa: E501
#     root_path="/api/v1",
#     docs_url=None,
#     openapi_url="/docs/openapi.json",
#     redoc_url="/docs",
# )
# api.add_middleware(GZipMiddleware, minimum_size=1000)
