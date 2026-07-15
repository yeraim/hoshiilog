from pathlib import Path
from typing import Any

from pydantic import PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.constants import Environment

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class CustomBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )


class Settings(CustomBaseSettings):
    APP_NAME: str = "Hoshiilog"
    DEBUG: bool = False
    LOG_LEVEL: str = "WARN"

    DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://user:pass@localhost/dbname"
    )
    DATABASE_ENGINE_POOL_SIZE: int = 20
    DATABASE_ENGINE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TTL: int = 60 * 20
    DATABASE_POOL_PRE_PING: bool = True
    # Redis is shared by arq's job queue, the crawler result cache, and pub/sub.
    # Defaults to the docker-compose `redis` service; override via env in deploy.
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: SecretStr = SecretStr("super-secret-key-for-dev")
    ALGORITHM: str = "HS256"

    # Crawler / marketplace adapter tuning.
    # Max concurrent outbound requests per marketplace (protects each site).
    MARKETPLACE_MAX_CONCURRENCY: int = 3
    # arq worker concurrency; bounded by Playwright memory budget in deploy.
    CRAWLER_MAX_JOBS: int = 10

    ENVIRONMENT: Environment = Environment.PRODUCTION

    SENTRY_DSN: str | None = None

    CORS_ORIGINS: list[str] = ["*"]
    CORS_ORIGINS_REGEX: str | None = None
    CORS_HEADERS: list[str] = ["*"]

    APP_VERSION: str = "0.1"

    @model_validator(mode="after")
    def validate_sentry_non_local(self) -> "Settings":
        if self.ENVIRONMENT.is_deployed and not self.SENTRY_DSN:
            raise ValueError("Sentry is not set")

        return self


settings = Settings()

app_configs: dict[str, Any] = {"title": "Hoshiilog API"}
if settings.ENVIRONMENT.is_deployed:
    app_configs["root_path"] = f"/v{settings.APP_VERSION}"

if not settings.ENVIRONMENT.is_debug:
    app_configs["openapi_url"] = None  # hide docs
