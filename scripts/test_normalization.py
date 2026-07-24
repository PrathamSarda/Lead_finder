from automation.intelligence.utils.normalizations import (
    normalize_url,
    domain,
    deduplicate_urls,
)

urls = [
    "https://www.linkedin.com/company/brockman-trucking-inc",
    "https://ch.linkedin.com/company/brockman-trucking-inc",
    "https://tr.linkedin.com/company/brockman-trucking-inc/",
    "https://nl.linkedin.com/company/brockman-trucking-inc",
]

print("Normalized URLs\n")

for url in urls:
    print(normalize_url(url))

print("\nDomain\n")
print(domain(urls[0]))

print("\nDeduplicated\n")

for url in deduplicate_urls(urls):
    print(url)