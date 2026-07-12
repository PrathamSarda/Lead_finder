from automation.enrichment.website_fetcher import fetch_website
from automation.enrichment.contact_page_finder import find_contact_pages


def main():

    url = "https://www.python.org"

    html = fetch_website(url)

    pages = find_contact_pages(html, url)

    print("\nPossible Contact Pages")
    print("-----------------------")

    for page in pages:
        print(page)


if __name__ == "__main__":
    main()