"""Redis keyspace, URL canonicalization, and (de)serialization for the crawler.

Single source of truth shared by the arq worker (writer) and the FastAPI routes
(reader/subscriber) so both sides agree on channel/key names and payload shape.

Keyspace for a job:
  lock:{job_id}                 SET NX EX 60  -> dedup / single-flight guard
  result:{job_id}:{marketplace} cached MatchResult JSON (TTL)
  result:{job_id}:done          "1" once the whole job finished (TTL)
  job:{job_id}                  pub/sub channel carrying JobEvent JSON

NOTE: results live only in Redis with a TTL for this pass. If results ever need
to be permanent, this is where a Postgres write-through would go.
"""

import hashlib
import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from redis.asyncio import Redis

from backend.app.presentation.schemas.crawler import (
    JobEvent,
    MatchResult,
    ProductInfo,
    SourceMarketplace,
)

log = logging.getLogger(__name__)

RESULT_TTL_SECONDS = 86_400  # 24h
LOCK_TTL_SECONDS = 60

# Query params dropped during canonicalization (tracking noise). All three
# marketplaces carry the product id in the URL *path*, so dropping query is safe
# for dedup.
_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"from", "sr", "advert", "abt_att", "miniapp", "share_from"}


def normalize_url(url: str) -> str:
    """Canonicalize a product URL for stable dedup / job-id hashing.

    Lowercases the host, drops the fragment and tracking query params, sorts the
    remaining query, and strips a trailing slash from the path.

    TODO: resolve short links (e.g. shared mobile-app links) here before hashing.
    """
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.port:
        host = f"{host}:{parsed.port}"
    kept = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if k not in _TRACKING_KEYS
        and not any(k.startswith(p) for p in _TRACKING_PREFIXES)
    ]
    query = urlencode(sorted(kept))
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), host, path, "", query, ""))


def compute_job_id(url: str) -> str:
    """Deterministic job id from the normalized URL (sha256, first 16 hex).

    Identical submissions map to the same job_id -> free dedup.
    """
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


# --- Key / channel names ---


def lock_key(job_id: str) -> str:
    return f"lock:{job_id}"


def channel(job_id: str) -> str:
    return f"job:{job_id}"


def result_key(job_id: str, marketplace: SourceMarketplace) -> str:
    return f"result:{job_id}:{marketplace}"


def done_key(job_id: str) -> str:
    return f"result:{job_id}:done"


def _result_scan_match(job_id: str) -> str:
    return f"result:{job_id}:*"


# --- Publish / cache (worker side) ---


def client_safe_event(event: JobEvent) -> JobEvent:
    """Copy of `event` with all `raw` debug fields dropped from its payload.

    `data` is a union (ProductInfo | MatchResult | None) and `raw` lives at
    different depths in each, so we sanitize via the models' own `to_client()`
    rather than a fragile static exclude path.
    """
    data = event.data
    if isinstance(data, (ProductInfo, MatchResult)):
        return event.model_copy(update={"data": data.to_client()})
    return event


async def publish_event(redis: Redis, event: JobEvent) -> None:
    """Publish a JobEvent to the job's pub/sub channel (never leaks `raw`)."""
    payload = client_safe_event(event).model_dump_json()
    await redis.publish(channel(event.job_id), payload)


async def cache_match_result(redis: Redis, job_id: str, result: MatchResult) -> None:
    # Cache client-safe: cached results are only ever read back to send to the
    # client, so `raw` is dropped here too.
    payload = result.to_client().model_dump_json()
    await redis.set(
        result_key(job_id, result.marketplace), payload, ex=RESULT_TTL_SECONDS
    )


async def mark_job_done(redis: Redis, job_id: str) -> None:
    await redis.set(done_key(job_id), "1", ex=RESULT_TTL_SECONDS)


# --- Read cached state (route side: GET polling + WS catch-up) ---


async def read_cached_state(
    redis: Redis, job_id: str
) -> tuple[list[MatchResult], bool]:
    """Return (cached MatchResults, done?) for a job from Redis.

    Works whether the job never started, is partially done, or fully finished —
    so both the polling endpoint and the WebSocket catch-up path use it.
    """
    results: list[MatchResult] = []
    done = False
    async for key in redis.scan_iter(match=_result_scan_match(job_id)):
        if key == done_key(job_id):
            done = True
            continue
        raw = await redis.get(key)
        if raw:
            results.append(MatchResult.model_validate_json(raw))
    # `scan_iter` may or may not surface the done flag depending on match; check
    # it explicitly to be safe.
    if not done:
        done = bool(await redis.exists(done_key(job_id)))
    return results, done
