from collections.abc import Callable
from typing import Optional

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from automation.browser.browser import BrowserManager


LoginVerifier = Callable[[Page], bool]


class SessionManager:
    """
    Manage manual authentication and persistent browser sessions.

    This class does not contain website-specific login selectors.
    Individual connectors will later provide their own session
    verification functions.
    """

    def __init__(
        self,
        source_name: str,
        login_url: str,
        home_url: Optional[str] = None,
    ) -> None:
        normalized_source_name = source_name.strip().lower()
        normalized_login_url = login_url.strip()

        if not normalized_source_name:
            raise ValueError("A source name must be provided.")

        if not normalized_login_url:
            raise ValueError("A login URL must be provided.")

        self.source_name = normalized_source_name
        self.login_url = normalized_login_url
        self.home_url = (
            home_url.strip()
            if home_url and home_url.strip()
            else None
        )

    def open_manual_login(
        self,
        verifier: Optional[LoginVerifier] = None,
    ) -> bool:
        """
        Open a visible persistent browser for manual login.

        The user completes credentials, OTP, CAPTCHA, or any other
        interactive login step and then confirms completion in the
        terminal.

        Args:
            verifier:
                Optional website-specific callback used to verify
                whether the page is authenticated.

        Returns:
            True when login is confirmed, otherwise False.
        """

        print(
            f"\nOpening persistent browser for "
            f"{self.source_name}..."
        )
        print(
            "Complete the login manually in the browser window."
        )
        print(
            "Do not close the browser manually. Return to this "
            "terminal after login is complete.\n"
        )

        with BrowserManager(
            source_name=self.source_name,
            headless=False,
        ) as browser:
            page = browser.get_page()
            page.goto(
                self.login_url,
                wait_until="domcontentloaded",
            )

            input(
                "After confirming that you are logged in, "
                "press ENTER here..."
            )

            if verifier is not None:
                try:
                    authenticated = verifier(page)
                except Exception as exc:
                    print(
                        "Session verification failed with an "
                        f"error: {exc}"
                    )
                    return False

                if not authenticated:
                    print(
                        "Login could not be verified. The browser "
                        "profile was preserved, but authentication "
                        "may be incomplete."
                    )
                    return False

            print(
                f"{self.source_name} browser profile was saved "
                "successfully."
            )

            return True

    def open_authenticated_session(
        self,
        verifier: Optional[LoginVerifier] = None,
        headless: bool = False,
    ) -> tuple[BrowserManager, Page]:
        """
        Open the existing persistent profile.

        Args:
            verifier:
                Optional callback that confirms whether the current
                session is still authenticated.
            headless:
                Whether to run Chromium without a visible window.

        Returns:
            A BrowserManager and active Page.

        Raises:
            RuntimeError:
                If a verifier is provided and the saved session is
                no longer authenticated.
        """

        browser = BrowserManager(
            source_name=self.source_name,
            headless=headless,
        )

        try:
            browser.start()
            page = browser.get_page()

            target_url = self.home_url or self.login_url

            page.goto(
                target_url,
                wait_until="domcontentloaded",
            )

            if verifier is not None and not verifier(page):
                raise RuntimeError(
                    f"The saved {self.source_name} session "
                    "is not authenticated."
                )

            return browser, page

        except Exception:
            browser.close()
            raise
