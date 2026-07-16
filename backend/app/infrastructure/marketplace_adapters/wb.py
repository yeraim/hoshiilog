"""Wildberries adapter — pure HTTP, no browser needed.

WB data comes from two very different surfaces:

  1. Basket CDN (static, NOT anti-bot protected) — reliable everywhere:
       card:   https://basket-XX.wbbasket.ru/vol{V}/part{P}/{nm}/info/ru/card.json
       image:  https://basket-XX.wbbasket.ru/vol{V}/part{P}/{nm}/images/big/1.webp
     card.json gives title (`imt_name`), brand (`selling.brand_name`), category,
     description, options — but NO price (price is dynamic).

  2. The `card.wb.ru` / `search.wb.ru` JSON APIs — carry live prices and search,
     but sit behind WB's anti-abuse layer ("wbaas") which returns 403/429 to
     datacenter / flagged IPs. So we treat these as BEST-EFFORT: price is
     `None` when blocked, and WB-as-a-search-target degrades to status="error"
     (isolated per-marketplace) rather than failing the whole job.

`nm` (nomenclature id) is the number in the path `/catalog/<nm>/detail.aspx`.
Prices, when reachable, live in `sizes[].price.{basic,product}` in kopeks (/100).

TODO(proxy): route the card.wb.ru / search.wb.ru calls through a CIS residential
proxy to get live prices and reliable WB search; without it those two are
best-effort. The basket CDN path needs no proxy.
"""

import asyncio
import logging
import re

import httpx

from backend.app.infrastructure.marketplace_adapters.base import (
    HTTP_TIMEOUT_SECONDS,
    AdapterError,
    BaseAdapter,
    build_search_query,
    rank_matches,
)
from backend.app.presentation.schemas.crawler import ProductInfo

log = logging.getLogger(__name__)

_DETAIL_URL = "https://card.wb.ru/cards/v2/detail"
_SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v18/search"
# Region/warehouse + currency; -1257786 is a common Moscow `dest`.
_COMMON_PARAMS = {"appType": "1", "curr": "rub", "dest": "-1257786", "spp": "30"}

# Browser-like headers reduce (but do not eliminate) wbaas 403s on the JSON APIs.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Origin": "https://www.wildberries.ru",
    "Referer": "https://www.wildberries.ru/",
}

_NM_RE = re.compile(r"/catalog/(\d+)")

# search.wb.ru rate-limits (429) bursts of requests. A short bounded backoff
# gets us past transient throttling without hammering. (Persistent 429 without
# a proxy still surfaces as an error — see TODO(proxy).)
_MAX_RETRIES = 3
_RETRY_STATUSES = {429, 503}


def _extract_products(payload: dict) -> list[dict]:
    """Pull the product list out of a WB JSON response.

    v18 returns `products`/`total` at the TOP level; older responses nested them
    under `data`. Handle both so a future version bump doesn't silently return
    zero matches.
    """
    if isinstance(payload.get("products"), list):
        return payload["products"]
    return (payload.get("data") or {}).get("products") or []


async def _get_json_with_retry(
    client: httpx.AsyncClient, url: str, params: dict
) -> dict:
    """GET + parse JSON, retrying on 429/503 with exponential backoff.

    On the final attempt `raise_for_status()` surfaces the status (so a
    persistent 429 becomes an httpx error the caller turns into an AdapterError).
    """
    for attempt in range(_MAX_RETRIES):
        resp = await client.get(url, params=params)
        if resp.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES - 1:
            await asyncio.sleep(0.5 * (2**attempt))  # 0.5s, 1s, 2s
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("unreachable")  # loop always returns or raises above


# Highest basket shard to probe. WB keeps adding shards; bump if new vols appear.
_MAX_BASKET_SHARD = 40

# Memoized vol -> basket shard, learned from successful card.json fetches. The
# WB vol->shard mapping drifts over time, so we discover it rather than hardcode.
_shard_cache: dict[int, int] = {}

# Coarse vol-range -> shard fallback, used only to guess images for search
# candidates (where probing every candidate would be too slow). Best-effort:
# a stale guess yields a wrong/404 image, never a failed job.
_BASKET_RANGES: list[tuple[int, int, int]] = [
    (0, 143, 1),
    (144, 287, 2),
    (288, 431, 3),
    (432, 719, 4),
    (720, 1007, 5),
    (1008, 1061, 6),
    (1062, 1115, 7),
    (1116, 1169, 8),
    (1170, 1313, 9),
    (1314, 1601, 10),
    (1602, 1655, 11),
    (1656, 1919, 12),
    (1920, 2045, 13),
    (2046, 2189, 14),
    (2190, 2405, 15),
    (2406, 2621, 16),
    (2622, 2837, 17),
    (2838, 3053, 18),
    (3054, 3269, 19),
    (3270, 3485, 20),
    (3486, 3701, 21),
    (3702, 3917, 22),
]


def _extract_nm(url: str) -> str:
    match = _NM_RE.search(url)
    if not match:
        raise AdapterError("wb", f"Could not extract nm id from URL: {url}")
    return match.group(1)


def _vol_part(nm: int) -> tuple[int, int]:
    return nm // 100_000, nm // 1_000


def _guess_shard(nm: int) -> int:
    vol, _ = _vol_part(nm)
    if vol in _shard_cache:
        return _shard_cache[vol]
    for low, high, shard in _BASKET_RANGES:
        if low <= vol <= high:
            return shard
    return 23  # beyond the known table: extrapolate to a higher shard


def _image_url(nm: int, shard: int) -> str:
    vol, part = _vol_part(nm)
    return (
        f"https://basket-{shard:02d}.wbbasket.ru"
        f"/vol{vol}/part{part}/{nm}/images/big/1.webp"
    )


async def _fetch_card_json(client: httpx.AsyncClient, nm: int) -> tuple[int, dict]:
    """Fetch a product's static card.json from the basket CDN.

    Discovers which basket shard serves this nm (trying the cached/guessed shard
    first, then scanning), and memoizes it per vol for subsequent calls.
    """
    vol, part = _vol_part(nm)
    tried: set[int] = set()
    order = [_guess_shard(nm)] + list(range(1, _MAX_BASKET_SHARD + 1))
    for shard in order:
        if shard in tried:
            continue
        tried.add(shard)
        url = (
            f"https://basket-{shard:02d}.wbbasket.ru"
            f"/vol{vol}/part{part}/{nm}/info/ru/card.json"
        )
        try:
            resp = await client.get(url)
        except httpx.HTTPError:
            continue
        if resp.status_code == 200:
            _shard_cache[vol] = shard
            try:
                return shard, resp.json()
            except ValueError as exc:
                raise AdapterError("wb", f"bad card.json for nm={nm}: {exc}") from exc
    raise AdapterError("wb", f"card.json not found on any basket shard for nm={nm}")


def _price_from_sizes(sizes: list[dict]) -> float | None:
    """Lowest available product price across sizes, in rubles."""
    prices: list[int] = []
    for size in sizes:
        price = size.get("price") or {}
        kopeks = price.get("product") or price.get("basic")
        if isinstance(kopeks, (int, float)):
            prices.append(int(kopeks))
    if not prices:
        return None
    return min(prices) / 100


async def _try_live_price(client: httpx.AsyncClient, nm: int) -> float | None:
    """Best-effort live price from card.wb.ru. Returns None if blocked (403/429).

    TODO(proxy): route through a CIS proxy so this succeeds reliably.
    """
    try:
        payload = await _get_json_with_retry(
            client, _DETAIL_URL, {**_COMMON_PARAMS, "nm": str(nm)}
        )
    except (httpx.HTTPError, ValueError):
        return None
    products = _extract_products(payload)
    if not products:
        return None
    return _price_from_sizes(products[0].get("sizes", []))


def _product_from_search_json(item: dict) -> ProductInfo:
    nm = int(item["id"])
    return ProductInfo(
        marketplace="wb",
        url=f"https://www.wildberries.ru/catalog/{nm}/detail.aspx",
        title=item.get("name", ""),
        price=_price_from_sizes(item.get("sizes", [])),
        currency="RUB",
        image_url=_image_url(nm, _guess_shard(nm)),  # best-effort image
        external_id=str(nm),
        brand=item.get("brand"),
        raw=item,
    )


class WildberriesAdapter(BaseAdapter):
    name = "wb"

    async def parse_product(self, url: str) -> ProductInfo:
        nm = int(_extract_nm(url))
        async with self._guard():
            async with httpx.AsyncClient(
                timeout=HTTP_TIMEOUT_SECONDS, headers=_HEADERS
            ) as client:
                # Metadata from the always-available basket CDN.
                shard, card = await _fetch_card_json(client, nm)
                # Price from the anti-bot-protected API — best-effort (may be None).
                price = await _try_live_price(client, nm)

        title = card.get("imt_name") or card.get("subj_name") or ""
        if not title:
            raise AdapterError("wb", f"card.json for nm={nm} had no title")
        brand = (card.get("selling") or {}).get("brand_name") or card.get("brand")
        return ProductInfo(
            marketplace="wb",
            url=url,
            title=title,
            price=price,
            currency="RUB",
            image_url=_image_url(nm, shard),
            external_id=str(nm),
            brand=brand,
            raw=card,
        )

    async def search_similar(
        self, query: ProductInfo, limit: int = 5
    ) -> list[ProductInfo]:
        q = build_search_query(query)
        if not q:
            return []
        params = {
            **_COMMON_PARAMS,
            "query": q,
            "resultset": "catalog",
            "sort": "popular",
            "page": "1",
            "suppressSpellcheck": "false",
        }
        # Best-effort: search.wb.ru is anti-bot protected and may 403/429 without
        # a CIS proxy, in which case this raises AdapterError and the job runner
        # records WB with status="error" (isolated from other marketplaces).
        try:
            async with self._guard():
                async with httpx.AsyncClient(
                    timeout=HTTP_TIMEOUT_SECONDS, headers=_HEADERS
                ) as client:
                    payload = await _get_json_with_retry(client, _SEARCH_URL, params)
        except (httpx.HTTPError, ValueError) as exc:
            raise AdapterError("wb", f"search failed: {exc}") from exc

        candidates = [
            _product_from_search_json(item) for item in _extract_products(payload)
        ]
        return rank_matches(query.title, candidates, limit=limit)
