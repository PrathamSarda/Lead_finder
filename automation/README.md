# Automation Module

Structural placeholder for a multi-source **company lead-finding pipeline**.
It intentionally contains no scraping/extraction logic — only the folder
layout and module boundaries a future implementation will use.

## What this pipeline is for

Finding US-based companies (1–15 employees) that are likely to need
bookkeeping services, and locating a contact email/phone for outreach.

## Layout

- `browser/` — shared Playwright session/context lifecycle helpers, reused
  across every source that requires a real browser (as opposed to a plain
  HTTP/API call).
- `sources/` — one submodule per data source. Each source is responsible
  only for *finding companies* and *extracting whatever contact info is
  visible on that source* — nothing else.
  - `linkedin/` — LinkedIn company search (Playwright-based).
  - `indeed/` — Indeed company/job listings search.
  - `google/` — Google search-based discovery (e.g. site: queries, local
    business results).
  - `wellfound/` — Wellfound (AngelList Talent) company search.
- `handlers/` — orchestration layer that ties sources together:
  - `search_handler.py` — runs the configured sources for a given query
    (industry/keyword + location + company size filter) and returns raw
    candidate companies.
  - `enrichment_handler.py` — takes candidate companies and fills in
    missing details (e.g. company size, website) from secondary lookups.
  - `email_finder.py` — attempts to resolve a contact email/phone for a
    company from the data collected across sources.
- `utils/` — shared helpers: deduplication, email format validation,
  domain/website resolution, rate limiting, logging.

## Notes

- Each source module should expose a consistent interface (e.g. a
  `search(criteria) -> list[CompanyCandidate]` function) so the handlers
  can treat all sources interchangeably. No such logic is implemented yet.
- Keep automation code isolated from the `backend/` API layer; the API
  should trigger automation jobs (e.g. via the scheduler or a queue) and
  persist their results, not contain scraping logic itself.
- Playwright is only needed for sources that require real browser
  rendering (e.g. LinkedIn, Wellfound). Sources with usable HTTP APIs
  (e.g. some Google/Indeed endpoints) may not need it at all — decide
  per-source when implementing.
