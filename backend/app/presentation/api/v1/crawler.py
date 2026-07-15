"""Crawler HTTP + WebSocket endpoints.

  POST /api/v1/crawler/searches            enqueue (or return cached / dedup)
  GET  /api/v1/crawler/searches/{job_id}   polling fallback (works without WS)
  WS   /api/v1/crawler/ws/{job_id}         live stream of results as they land

(The spec sketched `/ws/crawler/{job_id}`; kept under the project's existing
`/api/v1` mount for consistency with every other router.)

The WS process holds the socket; the arq worker publishes to Redis pub/sub and
this handler relays each event to the client.
"""

import asyncio
import logging

from arq import ArqRedis
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from backend.app.infrastructure.crawler_cache import (
    LOCK_TTL_SECONDS,
    channel,
    client_safe_event,
    compute_job_id,
    done_key,
    lock_key,
    normalize_url,
    read_cached_state,
)
from backend.app.infrastructure.redis import get_redis
from backend.app.presentation.schemas.crawler import (
    JobEvent,
    MatchResult,
    SearchRequest,
)

log = logging.getLogger(__name__)

crawler_router = APIRouter()

_TERMINAL_EVENTS = {"job_done", "job_error"}


def _result_payload(result: MatchResult) -> dict:
    # `raw` debug fields never go to the client (cache is already client-safe,
    # but sanitize defensively).
    return result.to_client().model_dump(mode="json")


@crawler_router.post("/searches")
async def create_search(req: SearchRequest, request: Request) -> dict:
    normalized = normalize_url(str(req.url))
    job_id = compute_job_id(normalized)
    redis = get_redis()
    try:
        # Fully-cached job? Return results immediately, create no job.
        if await redis.exists(done_key(job_id)):
            results, _done = await read_cached_state(redis, job_id)
            return {
                "job_id": job_id,
                "status": "cached",
                "results": [_result_payload(r) for r in results],
            }

        # Single-flight: only the lock winner enqueues; others just attach.
        acquired = await redis.set(lock_key(job_id), "1", nx=True, ex=LOCK_TTL_SECONDS)
        if not acquired:
            return {"job_id": job_id, "status": "already_running"}

        pool: ArqRedis = request.app.state.arq_pool
        # `_job_id=job_id` gives arq-level dedup on top of the Redis lock.
        await pool.enqueue_job("run_crawl_job", job_id, normalized, _job_id=job_id)
        return {"job_id": job_id, "status": "started"}
    finally:
        await redis.aclose()


@crawler_router.get("/searches/{job_id}")
async def get_search(job_id: str) -> dict:
    """Polling fallback — returns current state from Redis, no WS required."""
    redis = get_redis()
    try:
        results, done = await read_cached_state(redis, job_id)
        return {
            "job_id": job_id,
            "status": "done" if done else "running",
            "done": done,
            "results": [_result_payload(r) for r in results],
        }
    finally:
        await redis.aclose()


async def _send_cached_catch_up(
    websocket: WebSocket, job_id: str, redis
) -> tuple[set[str], bool]:
    """Send any already-cached state as JobEvents. Returns (sent_marketplaces, done)."""
    results, done = await read_cached_state(redis, job_id)
    sent: set[str] = set()
    if results:
        # Source product is embedded in every MatchResult; emit it once first.
        source_event = JobEvent(
            job_id=job_id, event="source_parsed", data=results[0].source
        )
        await websocket.send_text(client_safe_event(source_event).model_dump_json())
        for result in results:
            event = JobEvent(job_id=job_id, event="match_found", data=result)
            await websocket.send_text(client_safe_event(event).model_dump_json())
            sent.add(result.marketplace)
    return sent, done


@crawler_router.websocket("/ws/{job_id}")
async def crawler_ws(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    try:
        # Subscribe BEFORE reading cache: a job may finish between the POST and
        # this connect, so we must not miss events published in that window.
        await pubsub.subscribe(channel(job_id))

        sent_marketplaces, done = await _send_cached_catch_up(websocket, job_id, redis)
        if done:
            await websocket.send_text(
                JobEvent(job_id=job_id, event="job_done").model_dump_json()
            )
            return

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload = message["data"]
            event = JobEvent.model_validate_json(payload)

            # Skip a marketplace we already replayed from cache (avoids a dup if
            # it landed in the subscribe->cache-read window).
            if (
                event.event == "match_found"
                and isinstance(event.data, MatchResult)
                and event.data.marketplace in sent_marketplaces
            ):
                continue
            if event.event == "match_found" and isinstance(event.data, MatchResult):
                sent_marketplaces.add(event.data.marketplace)

            await websocket.send_text(payload)
            if event.event in _TERMINAL_EVENTS:
                break
    except WebSocketDisconnect:
        log.info("crawler ws client disconnected", extra={"job_id": job_id})
    except asyncio.CancelledError:
        raise
    except Exception:
        log.exception("crawler ws error", extra={"job_id": job_id})
    finally:
        try:
            await pubsub.unsubscribe(channel(job_id))
            await pubsub.aclose()
        finally:
            await redis.aclose()
        try:
            await websocket.close()
        except RuntimeError:
            pass  # already closed
