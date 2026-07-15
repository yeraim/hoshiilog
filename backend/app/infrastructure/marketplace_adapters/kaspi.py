"""Kaspi.kz adapter — Playwright (headless Chromium).

Kaspi has no usable public catalog API: the merchant API is auth-only and the
storefront is a client-rendered SPA behind aggressive anti-bot (IP/behavioral/
fingerprint). Community parsers all drive a headless browser and scrape the DOM,
so this adapter does the same via the shared `browser_pool`.

The DOM selectors below are best-effort and WILL drift as Kaspi changes markup.

TODO(proxy/stealth): a real deployment needs KZ residential proxies, a stealth
fingerprint, and a `kaspi.kz` city cookie to reliably get past anti-bot. Wiring
that is explicitly out of scope for this pass — without it these calls will
often be challenged/blocked and surface as `AdapterError`.
"""

import logging
import re
from urllib.parse import quote_plus

from playwright.async_api import Error as PlaywrightError

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

_SEARCH_URL = "https://kaspi.kz/shop/search/?text={q}"
_ID_RE = re.compile(r"/p/(?:c-)?(?:.*-)?(\d+)")
_DIGITS_RE = re.compile(r"\d+")


def _extract_id(url: str) -> str | None:
    match = _ID_RE.search(url)
    return match.group(1) if match else None


def _parse_price(text: str | None) -> float | None:
    if not text:
        return None
    digits = "".join(_DIGITS_RE.findall(text))
    return float(digits) if digits else None


async def _text_or_none(page, selector: str) -> str | None:
    try:
        el = await page.query_selector(selector)
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


class KaspiAdapter(BaseAdapter):
    name = "kaspi"

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
                    title = await _text_or_none(page, ".item__heading")
                    price = _parse_price(await _text_or_none(page, ".item__price-once"))
                    image = await _attr_or_none(page, ".item__slider-main img", "src")
        except PlaywrightError as exc:
            raise AdapterError("kaspi", f"parse_product failed: {exc}") from exc

        if not title:
            raise AdapterError(
                "kaspi",
                "could not extract title (likely anti-bot block or markup drift)",
            )
        return ProductInfo(
            marketplace="kaspi",
            url=url,
            title=title,
            price=price,
            currency="KZT",
            image_url=image,
            external_id=_extract_id(url),
            brand=None,  # TODO: pull brand from the spec table when reliably rendered.
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
                    cards = await page.query_selector_all(".item-card")
                    for card in cards[: limit * 3]:
                        name_el = await card.query_selector(".item-card__name")
                        link_el = await card.query_selector("a.item-card__name-link")
                        price_el = await card.query_selector(".item-card__prices-price")
                        title = (
                            (await name_el.inner_text()).strip() if name_el else None
                        )
                        href = await link_el.get_attribute("href") if link_el else None
                        if not title or not href:
                            continue
                        if href.startswith("/"):
                            href = f"https://kaspi.kz{href}"
                        candidates.append(
                            ProductInfo(
                                marketplace="kaspi",
                                url=href,
                                title=title,
                                price=_parse_price(
                                    await price_el.inner_text() if price_el else None
                                ),
                                currency="KZT",
                                image_url=None,
                                external_id=_extract_id(href),
                                brand=None,
                                raw=None,
                            )
                        )
        except PlaywrightError as exc:
            raise AdapterError("kaspi", f"search failed: {exc}") from exc

        return rank_matches(query.title, candidates, limit=limit)
