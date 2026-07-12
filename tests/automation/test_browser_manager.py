import pytest

from automation.browser.browser import BrowserManager
from automation.browser.session import SessionManager


def test_browser_manager_rejects_empty_source_name():
    with pytest.raises(ValueError):
        BrowserManager("")


def test_browser_context_requires_start():
    browser = BrowserManager("test-source")

    with pytest.raises(RuntimeError):
        _ = browser.context


def test_session_manager_rejects_empty_source_name():
    with pytest.raises(ValueError):
        SessionManager(
            source_name="",
            login_url="https://example.com/login",
        )


def test_session_manager_rejects_empty_login_url():
    with pytest.raises(ValueError):
        SessionManager(
            source_name="monster",
            login_url="",
        )