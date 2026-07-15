"""Shared Redis wiring for arq, the crawler result cache, and pub/sub.

All Redis access in the crawler funnels through here so there is a single
source of truth for connection settings (reused from `settings.REDIS_URL`,
never a second hardcoded URL).
"""

import asyncio
import logging

from arq.connections import RedisSettings
from redis.asyncio import Redis

from backend.app.config import settings

log = logging.getLogger(__name__)


def arq_redis_settings() -> RedisSettings:
    """arq's connection config, derived from the project's REDIS_URL."""
    return RedisSettings.from_dsn(settings.REDIS_URL)


def get_redis() -> Redis:
    """A `redis.asyncio` client for our own keys / pub/sub.

    `decode_responses=True` so cached JSON payloads and pub/sub messages come
    back as `str`. Callers own the lifecycle and must `aclose()` when done
    (the WebSocket handler does this in a `finally` block).
    """
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


class RedisSemaphore:
    """A best-effort, Redis-backed bounded counter used as a semaphore.

    Bounds concurrent outbound requests *per marketplace* across every arq job
    and worker replica (an in-process `asyncio.Semaphore` could not do this
    since jobs run concurrently within one worker and workers can be scaled
    horizontally). Fair enough for polite rate-limiting; not a strict
    distributed lock.
    """

    def __init__(
        self,
        redis: Redis,
        key: str,
        limit: int,
        *,
        max_wait: float = 30.0,
        poll_interval: float = 0.1,
        ttl: int = 60,
    ) -> None:
        self._redis = redis
        self._key = key
        self._limit = limit
        self._max_wait = max_wait
        self._poll = poll_interval
        self._ttl = ttl
        self._held = False

    async def __aenter__(self) -> "RedisSemaphore":
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._max_wait
        while True:
            current = await self._redis.incr(self._key)
            # Refresh TTL so a crashed holder can't leak a slot forever.
            await self._redis.expire(self._key, self._ttl)
            if current <= self._limit:
                self._held = True
                return self
            # Over the cap: give the slot back and wait for one to free up.
            await self._redis.decr(self._key)
            if loop.time() >= deadline:
                raise TimeoutError(
                    f"Timed out acquiring semaphore {self._key} (limit={self._limit})"
                )
            await asyncio.sleep(self._poll)

    async def __aexit__(self, *_exc: object) -> None:
        if not self._held:
            return
        self._held = False
        # Never let the counter drift below zero on races.
        new_value = await self._redis.decr(self._key)
        if new_value < 0:
            await self._redis.set(self._key, 0)


def marketplace_semaphore(redis: Redis, marketplace: str) -> RedisSemaphore:
    """Semaphore bounding concurrent requests to a single marketplace."""
    return RedisSemaphore(
        redis,
        key=f"sem:marketplace:{marketplace}",
        limit=settings.MARKETPLACE_MAX_CONCURRENCY,
    )
