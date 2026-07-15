"""Shared contract + helpers for marketplace adapters.

Each adapter knows how to (a) parse a product from a direct URL on its own site
and (b) search its own catalog for products similar to a source product from a
*different* site. Everything network-facing raises `AdapterError` on failure so
the job runner can turn one marketplace's failure into a per-marketplace
`status="error"` without killing the whole job.
"""

import re
from contextlib import AbstractAsyncContextManager, nullcontext
from typing import Protocol, runtime_checkable

from rapidfuzz import fuzz
from redis.asyncio import Redis

from backend.app.infrastructure.redis import marketplace_semaphore
from backend.app.presentation.schemas.crawler import ProductInfo, SourceMarketplace

# --- Tunables (kept as module constants so they're easy to find/adjust) ---

# Candidates whose title similarity to the source is below this are dropped.
# Start conservative; tune against real result quality later.
MIN_SIMILARITY_SCORE = 55

# Explicit timeouts on every outbound call (never rely on library defaults).
HTTP_TIMEOUT_SECONDS = 10.0
PLAYWRIGHT_GOTO_TIMEOUT_MS = 15_000

# Query-building noise words to strip when turning a title into a search query.
# Mostly Russian filler + unit tokens; extend as needed.
_NOISE_WORDS = {
    "и",
    "для",
    "с",
    "в",
    "на",
    "от",
    "по",
    "the",
    "for",
    "with",
    "шт",
    "мл",
    "гр",
    "г",
    "кг",
    "см",
    "мм",
    "set",
    "набор",
    "новинка",
    "оригинал",
    "official",
}

_TOKEN_RE = re.compile(r"[0-9a-zA-Zа-яёА-ЯЁ]+")


class AdapterError(Exception):
    """Raised by any adapter when parsing/searching fails.

    Carries the marketplace so the job runner can attribute the failure without
    parsing the message.
    """

    def __init__(self, marketplace: SourceMarketplace, message: str) -> None:
        self.marketplace = marketplace
        self.message = message
        super().__init__(f"[{marketplace}] {message}")


@runtime_checkable
class MarketplaceAdapter(Protocol):
    name: SourceMarketplace

    async def parse_product(self, url: str) -> ProductInfo:
        """Extract product info from a direct product URL on this marketplace."""
        ...

    async def search_similar(
        self, query: ProductInfo, limit: int = 5
    ) -> list[ProductInfo]:
        """Search this marketplace's catalog for products matching `query`."""
        ...


class BaseAdapter:
    """Common concurrency-guard plumbing shared by concrete adapters.

    Concrete adapters still satisfy `MarketplaceAdapter` structurally; this base
    only supplies the per-marketplace semaphore guard so every network call can
    be wrapped in `async with self._guard():`.
    """

    name: SourceMarketplace

    def __init__(self, redis: Redis | None = None) -> None:
        # `redis` is None in unit tests (adapters are mocked), which turns the
        # guard into a no-op. In the worker it's the arq/ctx redis client.
        self._redis = redis

    def _guard(self) -> AbstractAsyncContextManager:
        if self._redis is None:
            return nullcontext()
        return marketplace_semaphore(self._redis, self.name)


def build_search_query(product: ProductInfo, max_tokens: int = 6) -> str:
    """Turn a source product's brand+title into a compact search query.

    Strips noise/stop words and de-dupes tokens, keeping the most informative
    leading nouns. Brand (if present) is prepended so it anchors the search.
    """
    tokens: list[str] = []
    seen: set[str] = set()

    parts: list[str] = []
    if product.brand:
        parts.append(product.brand)
    parts.append(product.title)

    for raw in _TOKEN_RE.findall(" ".join(parts)):
        low = raw.lower()
        if low in _NOISE_WORDS or low in seen or len(low) < 2:
            continue
        seen.add(low)
        tokens.append(raw)
        if len(tokens) >= max_tokens:
            break
    return " ".join(tokens)


def rank_matches(
    source_title: str,
    candidates: list[ProductInfo],
    *,
    limit: int,
    min_score: int = MIN_SIMILARITY_SCORE,
) -> list[ProductInfo]:
    """Filter candidates by title similarity to the source, best first.

    Uses `token_sort_ratio` so word order differences don't tank the score.
    """
    scored: list[tuple[float, ProductInfo]] = []
    for candidate in candidates:
        score = fuzz.token_sort_ratio(source_title, candidate.title)
        if score >= min_score:
            scored.append((score, candidate))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [candidate for _score, candidate in scored[:limit]]
