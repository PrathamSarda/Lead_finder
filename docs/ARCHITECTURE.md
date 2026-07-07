# Architecture Overview

This document describes the high-level structure of the project. It is a
starter foundation — no scraping/business logic is implemented.

## Product context

The goal of the automation pipeline is to find US-based companies with
1–15 employees that are likely to need bookkeeping services, and resolve
a contact email/phone for outreach, using multiple sources: LinkedIn,
Indeed, Google Search, and Wellfound.

## Components

- **frontend/** — React (Vite) SPA. Talks to the backend exclusively via
  the REST API under `/api/v1`. Uses React Query for server state and
  React Context for auth state.
- **backend/** — FastAPI application. Organized by layer:
  - `app/api/` — HTTP routers (versioned under `v1/`).
  - `app/core/` — configuration and security primitives.
  - `app/db/` — SQLAlchemy engine/session and declarative base.
  - `app/models/` — ORM models: `User` (app login) and `Company` (a
    discovered lead).
  - `app/schemas/` — Pydantic request/response schemas.
  - `app/services/` — business logic layer (empty in this template).
  - `app/scheduler/` — APScheduler wiring for background jobs (e.g. to
    periodically trigger the automation pipeline once implemented).
- **automation/** — multi-source company/lead discovery scaffold:
  - `browser/` — shared Playwright session/context lifecycle, reused by
    any source that needs real browser rendering.
  - `sources/linkedin/`, `sources/indeed/`, `sources/google/`,
    `sources/wellfound/` — one module per data source, each responsible
    only for finding companies + whatever contact info is visible there.
  - `handlers/` — orchestration: `search_handler.py` fans out to sources,
    `enrichment_handler.py` fills in missing company details,
    `email_finder.py` resolves a contact email/phone.
  - `utils/` — deduplication, validation, and logging helpers shared
    across sources and handlers.
  Structurally isolated from the backend; intended to be triggered by
  scheduled jobs or backend-issued tasks, and to persist results via the
  `Company` model/API — not to contain API logic itself.
- **database/** — migration notes and local init scripts. Actual schema
  lives in SQLAlchemy models + Alembic migrations.
- **tests/** — test suites, mirroring the top-level module layout.
- **scripts/** — one-off and operational scripts (setup, seeding, etc).

## Request flow

```
Browser (React SPA)
   │  HTTPS (JWT bearer token)
   ▼
FastAPI (backend/app/main.py)
   │  SQLAlchemy session
   ▼
PostgreSQL
```

## Authentication flow

1. `POST /api/v1/auth/register` creates a user with a hashed password.
2. `POST /api/v1/auth/login` verifies credentials and issues a short-lived
   access token and a longer-lived refresh token (both JWTs).
3. The frontend stores both tokens and attaches the access token as a
   `Bearer` header on every request via an Axios interceptor.
4. On a 401 response, the same interceptor transparently calls
   `POST /api/v1/auth/refresh` and retries the original request once.

## Intended lead-discovery flow (not yet implemented)

```
scheduler (or manual trigger)
   │
   ▼
automation.handlers.search_handler
   │  fans out to each source
   ▼
sources.{linkedin,indeed,google,wellfound}.search(criteria)
   │  raw candidate companies
   ▼
automation.utils.dedup
   │  deduplicated candidates
   ▼
automation.handlers.enrichment_handler
   │  filled-in company details
   ▼
automation.handlers.email_finder
   │  companies + contact info
   ▼
backend Company model (persisted via POST /api/v1/companies)
```

## Extending this template

- Add new domain models under `backend/app/models/`, import them in
  `backend/app/db/base.py`, then generate a migration.
- Add new routers under `backend/app/api/v1/endpoints/` and register
  them in `backend/app/api/v1/api.py`.
- Add new pages under `frontend/src/pages/` and register routes in
  `frontend/src/routes/AppRoutes.jsx`.
- Implement each source's `search()` function under `automation/sources/`,
  then wire up the handlers in `automation/handlers/`.
