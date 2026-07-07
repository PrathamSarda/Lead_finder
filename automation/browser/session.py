"""
Placeholder for shared Playwright browser/context lifecycle management.

Sources that require real browser rendering (e.g. linkedin/, wellfound/)
are expected to obtain a browser/context from here rather than launching
their own, so session reuse, headless config, and cleanup stay centralized.

No implementation in this starter template.
"""
