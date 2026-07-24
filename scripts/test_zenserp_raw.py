from dotenv import load_dotenv

from automation.resolvers.providers.zenserp_provider import (
    ZenserpProvider,
)

load_dotenv()

provider = ZenserpProvider()

results = provider.search(
    'site:linkedin.com/company "BROCKMAN TRUCKING INC"'
)

print()
print("=" * 80)
print(f"Parsed results: {len(results)}")
print("=" * 80)

for result in results:
    print()
    print("Title:", result.title)
    print("URL:", result.url)
    print("Snippet:", result.snippet)