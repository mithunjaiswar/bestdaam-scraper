import os

from playwright.async_api import (
    Browser as AsyncBrowser,
    BrowserContext as AsyncBrowserContext,
    Page as AsyncPage,
    Playwright as AsyncPlaywright,
    async_playwright,
)

from playwright.sync_api import (
    Browser as SyncBrowser,
    BrowserContext as SyncBrowserContext,
    Page as SyncPage,
    Playwright as SyncPlaywright,
    sync_playwright,
)


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)


def use_headless_browser() -> bool:
    return os.environ.get("HEADLESS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


# ============================================================
# ASYNC BROWSER
# Used by amazon_test.py
# ============================================================

class BrowserManager:
    def __init__(self) -> None:
        self.playwright: AsyncPlaywright | None = None
        self.browser: AsyncBrowser | None = None
        self.context: AsyncBrowserContext | None = None
        self.page: AsyncPage | None = None

    async def start(self) -> AsyncPage:
        try:
            self.playwright = await async_playwright().start()

            self.browser = await self.playwright.chromium.launch(
                headless=use_headless_browser()
            )

            self.context = await self.browser.new_context(
                viewport={
                    "width": 1400,
                    "height": 900,
                },
                user_agent=USER_AGENT,
            )

            self.page = await self.context.new_page()

            return self.page

        except Exception:
            await self.close()
            raise

    async def close(self) -> None:
        if self.context is not None:
            try:
                await self.context.close()
            except Exception as error:
                print(f"Async context close warning: {error}")
            finally:
                self.context = None

        if self.browser is not None:
            try:
                await self.browser.close()
            except Exception as error:
                print(f"Async browser close warning: {error}")
            finally:
                self.browser = None

        if self.playwright is not None:
            try:
                await self.playwright.stop()
            except Exception as error:
                print(f"Async Playwright stop warning: {error}")
            finally:
                self.playwright = None

        self.page = None


# ============================================================
# SYNC BROWSER
# Used by main.py and Flipkart scraper
# ============================================================

class SyncBrowserManager:
    def __init__(self) -> None:
        self.playwright: SyncPlaywright | None = None
        self.browser: SyncBrowser | None = None
        self.context: SyncBrowserContext | None = None
        self.page: SyncPage | None = None

    def start(self) -> SyncPage:
        try:
            self.playwright = sync_playwright().start()

            self.browser = self.playwright.chromium.launch(
                headless=use_headless_browser()
            )

            self.context = self.browser.new_context(
                viewport={
                    "width": 1400,
                    "height": 900,
                },
                user_agent=USER_AGENT,
            )

            self.page = self.context.new_page()

            return self.page

        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self.context is not None:
            try:
                self.context.close()
            except Exception as error:
                print(f"Sync context close warning: {error}")
            finally:
                self.context = None

        if self.browser is not None:
            try:
                self.browser.close()
            except Exception as error:
                print(f"Sync browser close warning: {error}")
            finally:
                self.browser = None

        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception as error:
                print(f"Sync Playwright stop warning: {error}")
            finally:
                self.playwright = None

        self.page = None
