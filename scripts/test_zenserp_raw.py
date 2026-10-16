import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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