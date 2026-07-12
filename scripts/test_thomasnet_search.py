from automation.browser.browser import BrowserManager
from automation.sources.thomasnet.search import ThomasNetSearch


def main() -> None:
    with BrowserManager(
        source_name="thomasnet",
        headless=False,
    ) as browser:
        page = browser.get_page()

        search = ThomasNetSearch(page)

        search.open()
        search.search("machine shops")

        print(f"\nThomasNet results URL: {page.url}")
        print("Search completed successfully.")

        input(
            "\nCheck the results page, then press ENTER to close..."
        )


if __name__ == "__main__":
    main()