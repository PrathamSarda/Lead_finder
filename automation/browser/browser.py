from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)


DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_VIEWPORT = {
    "width": 1440,
    "height": 900,
}

PROFILES_DIRECTORY = Path(__file__).resolve().parent / "profiles"


class BrowserManager:
    """
    Manage a persistent Playwright Chromium browser context.

    Each source receives its own profile directory so cookies,
    local storage, preferences, and other browser state remain
    isolated from other website connectors.
    """

    def __init__(
        self,
        source_name: str,
        headless: bool = False,
        slow_mo: int = 0,
    ) -> None:
        normalized_source_name = source_name.strip().lower()

        if not normalized_source_name:
            raise ValueError("A source name must be provided.")

        self.source_name = normalized_source_name
        self.headless = headless
        self.slow_mo = slow_mo

        self.profile_directory = (
            PROFILES_DIRECTORY / self.source_name
        )

        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None

    @property
    def context(self) -> BrowserContext:
        """
        Return the active browser context.

        Raises:
            RuntimeError: If the browser has not been started.
        """

        if self._context is None:
            raise RuntimeError(
                "Browser context is not active. "
                "Call start() before accessing it."
            )

        return self._context

    def start(self) -> BrowserContext:
        """
        Start a persistent Chromium context for the source.

        Returns:
            The active persistent browser context.
        """

        if self._context is not None:
            return self._context

        self.profile_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._playwright = sync_playwright().start()

        try:
            self._context = (
                self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_directory),
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                    viewport=DEFAULT_VIEWPORT,
                    locale="en-US",
                    accept_downloads=True,
                )
            )

            self._context.set_default_timeout(
                DEFAULT_TIMEOUT_MS
            )

            return self._context

        except Exception:
            self._playwright.stop()
            self._playwright = None
            raise

    def get_page(self) -> Page:
        """
        Return the first open page or create a new one.
        """

        context = self.context

        if context.pages:
            return context.pages[0]

        return context.new_page()

    def new_page(self) -> Page:
        """
        Create and return a new browser page.
        """

        return self.context.new_page()

    def close(self) -> None:
        """
        Close the browser context and Playwright cleanly.
        """

        if self._context is not None:
            self._context.close()
            self._context = None

        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> "BrowserManager":
        self.start()
        return self

    def __exit__(
        self,
        exception_type,
        exception_value,
        traceback,
    ) -> None:
        self.close()
