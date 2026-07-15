"""arq worker that runs crawl jobs in a process separate from FastAPI.

Flow (see `run_crawl_job`): detect source marketplace -> parse source product ->
concurrently search the *other* marketplaces -> publish each result to Redis
pub/sub the moment it's ready (so a fast marketplace isn't held back by a slow
one) -> publish a final `job_done`.

The worker can't touch the WebSocket (different process), so all client-bound
communication goes out over Redis pub/sub; the FastAPI WS handler relays it.

Run with:  arq backend.app.workers.crawler_worker.WorkerSettings
"""

import asyncio
import logging

from redis.asyncio import Redis

from backend.app.config import settings
from backend.app.infrastructure.browser_pool import browser_pool
from backend.app.infrastructure.crawler_cache import (
    cache_match_result,
    mark_job_done,
    publish_event,
)
from backend.app.infrastructure.marketplace_adapters import (
    ALL_MARKETPLACES,
    AdapterError,
    detect_marketplace,
    get_adapter,
)
from backend.app.infrastructure.redis import arq_redis_settings
from backend.app.logging import configure_logging
from backend.app.presentation.schemas.crawler import (
    JobEvent,
    MatchResult,
    ProductInfo,
    SourceMarketplace,
)

configure_logging()
log = logging.getLogger(__name__)


async def _search_one(
    redis: Redis,
    job_id: str,
    source: ProductInfo,
    target: SourceMarketplace,
) -> MatchResult:
    """Search a single target marketplace, mapping failures to a MatchResult.

    Never raises for a marketplace failure: an `AdapterError` (or anything else)
    becomes `status="error"` so one marketplace can't sink the whole job.
    """
    adapter = get_adapter(target, redis=redis)
    try:
        matches = await adapter.search_similar(source)
        status = "ok" if matches else "not_found"
        result = MatchResult(
            source=source, matches=matches, marketplace=target, status=status
        )
        log.info(
            "adapter search complete",
            extra={"job_id": job_id, "marketplace": target, "matches": len(matches)},
        )
        return result
    except AdapterError as exc:
        log.warning(
            "adapter search failed",
            extra={"job_id": job_id, "marketplace": target, "error": exc.message},
        )
        # TODO(retry): retry/backoff for transient marketplace failures would go
        # here (bounded retries before giving up). Out of scope for this pass.
        return MatchResult(
            source=source,
            matches=[],
            marketplace=target,
            status="error",
            error=exc.message,
        )
    except Exception as exc:  # noqa: BLE001 - defensive: keep the job alive
        log.exception(
            "unexpected adapter error",
            extra={"job_id": job_id, "marketplace": target},
        )
        return MatchResult(
            source=source,
            matches=[],
            marketplace=target,
            status="error",
            error=f"unexpected error: {type(exc).__name__}",
        )


async def run_crawl_job(ctx: dict, job_id: str, url: str) -> None:
    redis: Redis = ctx["redis"]
    log.info("crawl job started", extra={"job_id": job_id, "url": url})

    try:
        source_mp = detect_marketplace(url)
        if source_mp is None:
            await publish_event(
                redis,
                JobEvent(
                    job_id=job_id,
                    event="job_error",
                    error="Unrecognized marketplace URL",
                ),
            )
            return

        # 1. Parse the source product and tell the client immediately.
        source_adapter = get_adapter(source_mp, redis=redis)
        try:
            source = await source_adapter.parse_product(url)
        except AdapterError as exc:
            log.warning(
                "source parse failed",
                extra={
                    "job_id": job_id,
                    "marketplace": source_mp,
                    "error": exc.message,
                },
            )
            await publish_event(
                redis,
                JobEvent(
                    job_id=job_id,
                    event="job_error",
                    error=f"Could not parse source product on {source_mp}",
                ),
            )
            return

        await publish_event(
            redis,
            JobEvent(job_id=job_id, event="source_parsed", data=source.to_client()),
        )

        # 2. Search the OTHER marketplaces concurrently; publish each as it lands.
        targets = [mp for mp in ALL_MARKETPLACES if mp != source_mp]
        tasks = [
            asyncio.create_task(_search_one(redis, job_id, source, mp))
            for mp in targets
        ]
        for coro in asyncio.as_completed(tasks):
            result = await coro
            await cache_match_result(redis, job_id, result)
            await publish_event(
                redis,
                JobEvent(job_id=job_id, event="match_found", data=result),
            )

        # 3. Mark done so late subscribers/pollers know the job fully finished.
        await mark_job_done(redis, job_id)
        await publish_event(redis, JobEvent(job_id=job_id, event="job_done"))
        log.info("crawl job done", extra={"job_id": job_id})

    except Exception:
        # Do not leak internals to the client; log the real error server-side.
        log.exception("crawl job failed", extra={"job_id": job_id})
        await publish_event(
            redis,
            JobEvent(
                job_id=job_id,
                event="job_error",
                error="Internal error while processing the job",
            ),
        )


async def startup(ctx: dict) -> None:
    # ctx["redis"] is provided by arq (an ArqRedis, which is a redis.asyncio
    # client). We also start the shared browser pool used by kaspi/ozon adapters.
    configure_logging()
    await browser_pool.start()
    log.info("crawler worker started")


async def shutdown(ctx: dict) -> None:
    await browser_pool.stop()
    log.info("crawler worker stopped")


class WorkerSettings:
    functions = [run_crawl_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = arq_redis_settings()
    max_jobs = settings.CRAWLER_MAX_JOBS
    job_timeout = 40  # whole job must not hang forever
    keep_result = 3600


__all__ = ["WorkerSettings", "run_crawl_job"]
