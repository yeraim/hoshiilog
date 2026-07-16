"""Ozon adapter — Playwright (headless Chromium).

Ozon *does* have a public internal JSON endpoint
(`https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=<path>`) that
returns product/search data in a `widgetStates` map (title in `webProductHeading`,
price in `webPrice`, etc.), but cold requests are cookie/fingerprint-gated and
rate-limited (~30-50 req/min -> 429). The robust path is to drive a headless
browser to establish a session and read the rendered React DOM.

TODO(optimize): once a browser session is warm, replay `entrypoint-api.bx` over
HTTP with the harvested cookies instead of scraping the DOM — much cheaper.
TODO(proxy/stealth): production needs stealth fingerprinting + proxies to beat
Ozon's anti-bot; out of scope for this pass, so DOM selectors below are
best-effort and will surface `AdapterError` when challenged.
"""

import logging
import re
from urllib.parse import quote_plus

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from backend.app.infrastructure.browser_pool import browser_pool
from backend.app.infrastructure.marketplace_adapters.base import (
    PLAYWRIGHT_GOTO_TIMEOUT_MS,
    AdapterError,
    BaseAdapter,
    build_search_query,
    rank_matches,
)
from backend.app.presentation.schemas.crawler import ProductInfo

log = logging.getLogger(__name__)

_SEARCH_URL = "https://www.ozon.ru/search/?text={q}"
# sku is the trailing number in `/product/<slug>-<sku>/`.
_SKU_RE = re.compile(r"/product/(?:.*-)?(\d+)")
_DIGITS_RE = re.compile(r"\d+")


def _extract_sku(url: str) -> str | None:
    match = _SKU_RE.search(url)
    return match.group(1) if match else None


def _parse_price(text: str | None) -> float | None:
    if not text:
        return None
    digits = "".join(_DIGITS_RE.findall(text))
    return float(digits) if digits else None


async def _text_or_none(page_or_el, selector: str) -> str | None:
    try:
        el = await page_or_el.query_selector(selector)
        if el is None:
            return None
        return (await el.inner_text()).strip()
    except PlaywrightError:
        return None


async def _attr_or_none(page, selector: str, attr: str) -> str | None:
    try:
        el = await page.query_selector(selector)
        if el is None:
            return None
        return await el.get_attribute(attr)
    except PlaywrightError:
        return None


class OzonAdapter(BaseAdapter):
    name = "ozon"

    async def parse_product(self, url: str) -> ProductInfo:
        try:
            async with self._guard():
                async with browser_pool.get_context() as context:
                    page = await context.new_page()
                    await page.goto(
                        url,
                        timeout=PLAYWRIGHT_GOTO_TIMEOUT_MS,
                        wait_until="domcontentloaded",
                    )
                    # SPA: wait for the product title to render.
                    try:
                        await page.wait_for_selector(
                            "h1", timeout=PLAYWRIGHT_GOTO_TIMEOUT_MS
                        )
                    except PlaywrightTimeoutError:
                        pass  # title stays None -> AdapterError below
                    # Ozon class names are obfuscated/rotating; anchor on the
                    # semantic h1 for the title and a price data attribute.
                    title = await _text_or_none(page, "h1")
                    price = _parse_price(
                        await _text_or_none(page, "[data-widget='webPrice']")
                    )
                    image = await _attr_or_none(
                        page, "[data-widget='webGallery'] img", "src"
                    )
        except PlaywrightError as exc:
            raise AdapterError("ozon", f"parse_product failed: {exc}") from exc

        if not title:
            raise AdapterError(
                "ozon",
                "could not extract title (likely anti-bot block or markup drift)",
            )
        return ProductInfo(
            marketplace="ozon",
            url=url,
            title=title,
            price=price,
            currency="RUB",
            image_url=image,
            external_id=_extract_sku(url),
            brand=None,
            raw=None,
        )

    async def search_similar(
        self, query: ProductInfo, limit: int = 5
    ) -> list[ProductInfo]:
        q = build_search_query(query)
        if not q:
            return []
        search_url = _SEARCH_URL.format(q=quote_plus(q))
        candidates: list[ProductInfo] = []
        try:
            async with self._guard():
                async with browser_pool.get_context() as context:
                    page = await context.new_page()
                    await page.goto(
                        search_url,
                        timeout=PLAYWRIGHT_GOTO_TIMEOUT_MS,
                        wait_until="domcontentloaded",
                    )
                    # Result tiles render via JS; wait for product anchors.
                    # A timeout means no results -> not_found.
                    try:
                        await page.wait_for_selector(
                            "a[href*='/product/']", timeout=PLAYWRIGHT_GOTO_TIMEOUT_MS
                        )
                    except PlaywrightTimeoutError:
                        return []
                    # Product tiles link to /product/...; harvest those anchors.
                    links = await page.query_selector_all("a[href*='/product/']")
                    seen: set[str] = set()
                    for link in links:
                        href = await link.get_attribute("href")
                        title = (await link.inner_text()).strip()
                        if not href or not title:
                            continue
                        if href.startswith("/"):
                            href = f"https://www.ozon.ru{href}"
                        sku = _extract_sku(href)
                        if not sku or sku in seen:
                            continue
                        seen.add(sku)
                        candidates.append(
                            ProductInfo(
                                marketplace="ozon",
                                url=href,
                                title=title,
                                price=None,  # price not reliably on the tile anchor
                                currency="RUB",
                                image_url=None,
                                external_id=sku,
                                brand=None,
                                raw=None,
                            )
                        )
                        if len(candidates) >= limit * 3:
                            break
        except PlaywrightError as exc:
            raise AdapterError("ozon", f"search failed: {exc}") from exc

        return rank_matches(query.title, candidates, limit=limit)
