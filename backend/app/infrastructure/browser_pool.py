"""Module-level Playwright browser singleton.

Launching a full Chromium is expensive (hundreds of ms + memory); creating a
`BrowserContext` from an already-running browser is cheap. So we keep ONE warm
browser for the lifetime of the arq worker process and hand out a fresh,
isolated context per job.

Lifecycle is owned by the arq worker:
  on_startup  -> await browser_pool.start()
  on_shutdown -> await browser_pool.stop()

The Kaspi and Ozon adapters use this; the WB adapter is pure HTTP and does not.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

log = logging.getLogger(__name__)

# A plain desktop UA. NOTE: a real deployment against Kaspi/Ozon needs proper
# stealth (fingerprint masking) + residential/KZ proxies to survive anti-bot;
# see the adapter TODOs. That is explicitly out of scope for this pass.
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class BrowserPool:
    """Owns a single headless Chromium and vends fresh contexts."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        if self._browser is not None:
            return
        log.info("Starting Playwright browser pool")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

    async def stop(self) -> None:
        log.info("Stopping Playwright browser pool")
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    @asynccontextmanager
    async def get_context(self) -> AsyncIterator[BrowserContext]:
        """Yield a fresh, isolated `BrowserContext`, closed on exit.

        Contexts are cheap and disposable — one per job keeps cookies/state
        from leaking between jobs. The browser itself is reused.
        """
        if self._browser is None:
            raise RuntimeError(
                "BrowserPool not started; call start() in the worker on_startup"
            )
        # TODO(proxy): pass proxy={"server": ...} per-marketplace here once
        # proxy rotation is wired up for a real deployment.
        context = await self._browser.new_context(user_agent=_DEFAULT_USER_AGENT)
        try:
            yield context
        finally:
            await context.close()


# Module-level singleton. The worker starts/stops it; adapters import and use it.
browser_pool = BrowserPool()
