from automation.extractors.website_extractor import WebsiteExtractor


def main():

    extractor = WebsiteExtractor()

    soup = extractor.fetch_page("https://openai.com")

    print("\nWebsite Title:")
    print(soup.title.text)


if __name__ == "__main__":
    main()