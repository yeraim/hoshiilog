"""Marketplace adapter registry: URL detection + factory.

`detect_marketplace` maps a URL's domain to a marketplace; `get_adapter` builds
the concrete adapter for a marketplace, injecting the Redis client used for the
per-marketplace concurrency semaphore.
"""

from urllib.parse import urlparse

from redis.asyncio import Redis

from backend.app.infrastructure.marketplace_adapters.base import (
    AdapterError,
    MarketplaceAdapter,
)
from backend.app.infrastructure.marketplace_adapters.kaspi import KaspiAdapter
from backend.app.infrastructure.marketplace_adapters.ozon import OzonAdapter
from backend.app.infrastructure.marketplace_adapters.wb import WildberriesAdapter
from backend.app.presentation.schemas.crawler import SourceMarketplace

# Domain substring -> marketplace. Matched against the URL host (suffix-aware).
_DOMAIN_MAP: dict[str, SourceMarketplace] = {
    "wildberries.ru": "wb",
    "wb.ru": "wb",
    "kaspi.kz": "kaspi",
    "ozon.ru": "ozon",
}

_ADAPTERS: dict[SourceMarketplace, type] = {
    "wb": WildberriesAdapter,
    "kaspi": KaspiAdapter,
    "ozon": OzonAdapter,
}

ALL_MARKETPLACES: tuple[SourceMarketplace, ...] = ("wb", "kaspi", "ozon")


def detect_marketplace(url: str) -> SourceMarketplace | None:
    """Return the marketplace a product URL belongs to, or None if unknown."""
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return None
    for domain, marketplace in _DOMAIN_MAP.items():
        # Suffix match so `www.wildberries.ru` and `global.wildberries.ru` both
        # resolve, without matching an unrelated host that merely contains it.
        if host == domain or host.endswith(f".{domain}"):
            return marketplace
    return None


def get_adapter(
    marketplace: SourceMarketplace, redis: Redis | None = None
) -> MarketplaceAdapter:
    """Build the adapter for `marketplace`, injecting `redis` for the semaphore."""
    try:
        adapter_cls = _ADAPTERS[marketplace]
    except KeyError:
        raise AdapterError(marketplace, f"no adapter for marketplace: {marketplace}")
    return adapter_cls(redis=redis)


__all__ = [
    "ALL_MARKETPLACES",
    "AdapterError",
    "MarketplaceAdapter",
    "detect_marketplace",
    "get_adapter",
]
