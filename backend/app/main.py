import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.app.api import api_router
from backend.app.config import app_configs, settings
from backend.app.database import engine
from backend.app.logging import configure_logging

log = logging.getLogger(__name__)
configure_logging()


async def not_found(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": [{"msg": "Not Found."}]},
    )


exception_handlers = {404: not_found}


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

    yield

    # --- Shutdown ---
    # Clean up resources, close connections, etc.
    await engine.dispose()


if settings.ENVIRONMENT.is_deployed:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
    )


app = FastAPI(**app_configs, lifespan=lifespan)

app.include_router(api_router)


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
#     description="Welcome to Dispatch's API documentation! Here you will able to discover all of the ways you can interact with the Dispatch API.",
#     root_path="/api/v1",
#     docs_url=None,
#     openapi_url="/docs/openapi.json",
#     redoc_url="/docs",
# )
# api.add_middleware(GZipMiddleware, minimum_size=1000)
