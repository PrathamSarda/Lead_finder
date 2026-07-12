from automation.enrichment.website_fetcher import fetch_website
from automation.enrichment.email_extractor import extract_emails


def main():

    url = "https://prokizen.com"
    html = fetch_website(url)

    emails = extract_emails(html)

    print()

    print("Emails Found")

    print("----------------")

    if not emails:
        print("No emails found.")

    else:
        for email in emails:
            print(email)


if __name__ == "__main__":
    main()

