"""Publish/consume round-trip and cache read-back using a fakeredis double.

No real Redis or marketplace network access — mirrors what the worker writes
and what the routes read.
"""

import pytest
from fakeredis import FakeAsyncRedis

from backend.app.infrastructure.crawler_cache import (
    cache_match_result,
    channel,
    done_key,
    mark_job_done,
    publish_event,
    read_cached_state,
)
from backend.app.presentation.schemas.crawler import (
    JobEvent,
    MatchResult,
    ProductInfo,
)

JOB_ID = "abc123def456"


async def _next_message(pubsub, tries: int = 5):
    """Poll past fakeredis's leading None (subscribe confirmation)."""
    for _ in range(tries):
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
        if msg is not None:
            return msg
    return None


def _source() -> ProductInfo:
    return ProductInfo(
        marketplace="wb",
        url="https://www.wildberries.ru/catalog/1/detail.aspx",
        title="Кроссовки Nike Air",
        price=9999.0,
        currency="RUB",
        external_id="1",
        brand="Nike",
        raw={"secret_internal_field": "should not reach client"},
    )


def _match_result() -> MatchResult:
    match = ProductInfo(
        marketplace="ozon",
        url="https://www.ozon.ru/product/nike-air-2/",
        title="Кроссовки Nike Air (Ozon)",
        price=10500.0,
        currency="RUB",
        external_id="2",
        brand="Nike",
        raw={"leak": "nope"},
    )
    return MatchResult(
        source=_source(),
        matches=[match],
        marketplace="ozon",
        status="ok",
        error=None,
    )


@pytest.fixture
def redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


async def test_publish_consume_round_trip(redis: FakeAsyncRedis) -> None:
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel(JOB_ID))

    event = JobEvent(job_id=JOB_ID, event="match_found", data=_match_result())
    await publish_event(redis, event)

    message = await _next_message(pubsub)
    assert message is not None
    received = JobEvent.model_validate_json(message["data"])

    assert received.job_id == JOB_ID
    assert received.event == "match_found"
    assert isinstance(received.data, MatchResult)
    assert received.data.marketplace == "ozon"
    assert received.data.matches[0].title == "Кроссовки Nike Air (Ozon)"

    await pubsub.unsubscribe(channel(JOB_ID))
    await pubsub.aclose()


async def test_published_payload_strips_raw_debug_fields(
    redis: FakeAsyncRedis,
) -> None:
    """`raw` must never leave the server in a published event."""
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel(JOB_ID))

    await publish_event(
        redis,
        JobEvent(job_id=JOB_ID, event="source_parsed", data=_source()),
    )
    message = await _next_message(pubsub)

    assert message is not None
    assert "secret_internal_field" not in message["data"]
    received = JobEvent.model_validate_json(message["data"])
    assert isinstance(received.data, ProductInfo)
    assert received.data.raw is None

    await pubsub.aclose()


async def test_cache_and_read_state(redis: FakeAsyncRedis) -> None:
    # Nothing cached yet.
    results, done = await read_cached_state(redis, JOB_ID)
    assert results == []
    assert done is False

    await cache_match_result(redis, JOB_ID, _match_result())
    results, done = await read_cached_state(redis, JOB_ID)
    assert len(results) == 1
    assert results[0].marketplace == "ozon"
    assert done is False

    await mark_job_done(redis, JOB_ID)
    results, done = await read_cached_state(redis, JOB_ID)
    assert done is True
    assert len(results) == 1  # done flag isn't counted as a result
    assert await redis.exists(done_key(JOB_ID)) == 1
