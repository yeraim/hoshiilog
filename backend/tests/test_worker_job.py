"""End-to-end worker run with mocked adapters (no network, no browser).

Verifies the worker publishes source_parsed -> match_found (per target) ->
job_done, and that one marketplace raising AdapterError becomes a per-market
`status="error"` MatchResult instead of failing the whole job.
"""

import pytest
from fakeredis import FakeAsyncRedis

from backend.app.infrastructure.marketplace_adapters.base import AdapterError
from backend.app.presentation.schemas.crawler import (
    JobEvent,
    MatchResult,
    ProductInfo,
)
from backend.app.workers import crawler_worker

JOB_ID = "job0001"
WB_URL = "https://www.wildberries.ru/catalog/1/detail.aspx"


class FakeAdapter:
    def __init__(self, name, *, matches=None, search_error=False):
        self.name = name
        self._matches = matches or []
        self._search_error = search_error

    async def parse_product(self, url: str) -> ProductInfo:
        return ProductInfo(
            marketplace=self.name, url=url, title="Nike Air", brand="Nike"
        )

    async def search_similar(self, query, limit: int = 5):
        if self._search_error:
            raise AdapterError(self.name, "simulated failure")
        return self._matches


async def _collect_events(pubsub, max_polls=15):
    """Drain published events. fakeredis returns None for the subscribe
    confirmation, so poll past leading/interleaved Nones until terminal."""
    events = []
    for _ in range(max_polls):
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
        if msg is None:
            continue
        event = JobEvent.model_validate_json(msg["data"])
        events.append(event)
        if event.event in ("job_done", "job_error"):
            break
    return events


@pytest.fixture
def redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


async def test_job_publishes_incrementally_and_isolates_errors(
    redis: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    ozon_match = ProductInfo(
        marketplace="ozon",
        url="https://www.ozon.ru/product/nike-2/",
        title="Nike Air Ozon",
        brand="Nike",
    )
    adapters = {
        "wb": FakeAdapter("wb"),
        "ozon": FakeAdapter("ozon", matches=[ozon_match]),
        "kaspi": FakeAdapter("kaspi", search_error=True),  # this one fails
    }
    monkeypatch.setattr(
        crawler_worker, "get_adapter", lambda mp, redis=None: adapters[mp]
    )

    pubsub = redis.pubsub()
    await pubsub.subscribe(f"job:{JOB_ID}")

    await crawler_worker.run_crawl_job({"redis": redis}, JOB_ID, WB_URL)

    events = await _collect_events(pubsub)
    kinds = [e.event for e in events]

    assert kinds[0] == "source_parsed"
    assert kinds[-1] == "job_done"
    assert kinds.count("match_found") == 2  # ozon + kaspi (source wb excluded)

    by_mp = {
        e.data.marketplace: e.data
        for e in events
        if e.event == "match_found" and isinstance(e.data, MatchResult)
    }
    assert by_mp["ozon"].status == "ok"
    assert by_mp["ozon"].matches[0].title == "Nike Air Ozon"
    # Failure isolated to the one marketplace.
    assert by_mp["kaspi"].status == "error"
    assert by_mp["kaspi"].error == "simulated failure"

    # done flag + cached results persisted.
    assert await redis.exists(f"result:{JOB_ID}:done") == 1
    assert await redis.exists(f"result:{JOB_ID}:ozon") == 1

    await pubsub.aclose()


async def test_unrecognized_url_publishes_job_error(
    redis: FakeAsyncRedis,
) -> None:
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"job:{JOB_ID}")

    await crawler_worker.run_crawl_job(
        {"redis": redis}, JOB_ID, "https://example.com/x"
    )

    events = await _collect_events(pubsub)
    assert len(events) == 1
    assert events[0].event == "job_error"
    assert events[0].error == "Unrecognized marketplace URL"

    await pubsub.aclose()
