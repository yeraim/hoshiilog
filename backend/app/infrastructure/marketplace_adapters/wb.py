"""Wildberries adapter — pure HTTP, no browser needed.

WB exposes everything we need over public, unauthenticated JSON:
  - detail:  https://card.wb.ru/cards/v2/detail?nm=<article>
  - search:  https://search.wb.ru/exactmatch/ru/common/v18/search?query=<q>
  - images:  computed basket-XX.wbbasket.ru CDN URL (no request needed)

The `nm` (nomenclature) id is simply the number in the product path
`/catalog/<nm>/detail.aspx`. Prices live in `sizes[].price.{basic,product}`
and are in kopeks (divide by 100).

These endpoints are undocumented and versioned (WB already moved search v4->v18
and migrated wb.ru->wbbasket.ru), so hosts/versions are kept as constants here
to make future bumps a one-line change.
"""

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

_NM_RE = re.compile(r"/catalog/(\d+)")

# vol-range -> basket shard. As of 2025; WB adds shards over time so this WILL
# drift. Image URLs are non-critical (best-effort), so a stale mapping only
# yields a wrong image, never a failed job. TODO: probe hosts or fetch an
# updatable table instead of hardcoding when images matter.
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


def _basket_host(nm: int) -> str:
    vol = nm // 100_000
    for low, high, shard in _BASKET_RANGES:
        if low <= vol <= high:
            return f"basket-{shard:02d}.wbbasket.ru"
    # Beyond the known table: extrapolate to a higher shard as a best guess.
    return "basket-23.wbbasket.ru"


def _image_url(nm: int) -> str:
    host = _basket_host(nm)
    return f"https://{host}/vol{nm // 100_000}/part{nm // 1_000}/{nm}/images/big/1.webp"


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


def _product_from_json(item: dict) -> ProductInfo:
    nm = int(item["id"])
    return ProductInfo(
        marketplace="wb",
        url=f"https://www.wildberries.ru/catalog/{nm}/detail.aspx",
        title=item.get("name", ""),
        price=_price_from_sizes(item.get("sizes", [])),
        currency="RUB",
        image_url=_image_url(nm),
        external_id=str(nm),
        brand=item.get("brand"),
        raw=item,
    )


class WildberriesAdapter(BaseAdapter):
    name = "wb"

    async def parse_product(self, url: str) -> ProductInfo:
        nm = _extract_nm(url)
        params = {**_COMMON_PARAMS, "nm": nm}
        try:
            async with self._guard():
                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                    resp = await client.get(_DETAIL_URL, params=params)
                    resp.raise_for_status()
                    payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AdapterError("wb", f"detail fetch failed: {exc}") from exc

        products = (payload.get("data") or {}).get("products") or []
        if not products:
            raise AdapterError("wb", f"no product found for nm={nm}")
        return _product_from_json(products[0])

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
        try:
            async with self._guard():
                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                    resp = await client.get(_SEARCH_URL, params=params)
                    resp.raise_for_status()
                    payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AdapterError("wb", f"search failed: {exc}") from exc

        raw_products = (payload.get("data") or {}).get("products") or []
        candidates = [_product_from_json(item) for item in raw_products]
        return rank_matches(query.title, candidates, limit=limit)
