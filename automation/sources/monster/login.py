from playwright.sync_api import Page


MONSTER_HOME_URL = "https://www.monster.com/"


def open_monster(page: Page) -> None:
    """
    Open the Monster US job-search page.
    """

    page.goto(
    MONSTER_HOME_URL,
    wait_until="commit",
)


def is_logged_in(page: Page) -> bool:
    """
    Temporary Monster authentication check.

    We will replace this with a reliable DOM-based check after
    inspecting the authenticated page.
    """

    return "monster.com" in page.url.lower()