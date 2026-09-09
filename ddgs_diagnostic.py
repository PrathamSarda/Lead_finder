"""
Minimal, isolated DDGS test -- no pipeline code involved.

Run this on its own to check whether DuckDuckGo is currently
rate-limiting or blocking this connection, separate from anything
in the lead pipeline.

    python ddgs_diagnostic.py
"""

from ddgs import DDGS

query = "Anthropic Claude AI"  # a query guaranteed to have results

print(f"Testing DDGS with query: {query!r}\n")

try:
    with DDGS() as ddgs:
        results = list(
            ddgs.text(
                query,
                region="us-en",
                safesearch="off",
                max_results=5,
                backend="duckduckgo",
            )
        )

    if results:
        print(f"SUCCESS: got {len(results)} result(s).")
        for r in results:
            print(" -", r.get("title"), "|", r.get("href"))
    else:
        print(
            "DDGS returned an empty list with no error. "
            "This points to DuckDuckGo blocking/throttling this "
            "IP rather than a code problem."
        )

except Exception as exc:
    print(f"DDGS raised an exception: {type(exc).__name__}: {exc}")
    print(
        "\nThis is likely a rate limit or block from DuckDuckGo's "
        "side, not a bug in the pipeline code."
    )