import requests
from bs4 import BeautifulSoup


class WebsiteExtractor:
    """
    Downloads a webpage and returns its HTML.
    """

    def fetch_page(self, url: str):

        print(f"\nVisiting: {url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            )
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=15,
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        return soup