# Company Lead Finder

A production-ready **foundation** for a SaaS application that finds
US-based companies (1–15 employees) likely to need bookkeeping services,
and resolves a contact email/phone for outreach — sourced across
LinkedIn, Indeed, Google Search, and Wellfound.

This is a scaffold, not a finished product. It ships with authentication,
routing, a clean backend architecture, and a reusable UI component set —
but no scraping/search logic.

## Tech stack

**Frontend** — React (Vite), Tailwind CSS, React Router, Axios, React Query, React Hook Form
**Backend** — FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic
**Auth** — JWT access + refresh tokens, bcrypt password hashing
**Automation** — Playwright (Python) — structural scaffold only, multi-source
**Scheduler** — APScheduler — wired up, no jobs registered

## Project structure

```
company-lead-finder/
│
├── frontend/                # React (Vite) SPA
│   └── src/
│       ├── api/               # Axios client + API modules (auth, companies)
│       ├── components/
│       │   ├── auth/           # ProtectedRoute
│       │   ├── layout/         # Navbar, Sidebar, Layout
│       │   └── ui/             # Button, Card, Table, Modal, Loading, Toast
│       ├── context/            # AuthContext
│       ├── hooks/               # React Query hooks (useCurrentUser, useCompanies)
│       ├── pages/                # Login, Dashboard, Companies, Settings, etc.
│       └── routes/                # Route definitions
│
├── backend/                  # FastAPI application
│   └── app/
│       ├── api/v1/             # Versioned routers (auth, users, companies)
│       ├── core/                 # Config + security (JWT, hashing)
│       ├── db/                    # SQLAlchemy engine/session/Base
│       ├── models/                 # User (login) + Company (lead) ORM models
│       ├── schemas/                  # Pydantic schemas
│       ├── services/                  # Business logic layer (empty)
│       └── scheduler/                  # APScheduler wiring (no jobs)
│
├── automation/                # Multi-source lead discovery scaffold (no logic)
│   ├── browser/                  # Shared Playwright session management
│   ├── sources/
│   │   ├── linkedin/
│   │   ├── indeed/
│   │   ├── google/
│   │   └── wellfound/
│   ├── handlers/                  # search / enrichment / email-finder orchestration
│   └── utils/                      # dedup, validation, logging helpers
│
├── database/                   # Migration notes + local init script
├── docs/                         # Architecture documentation
├── tests/                          # Test suites (backend/frontend/automation)
├── scripts/                         # Setup, migration, and seed scripts
│
├── .env.example
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Getting started

### Option A — Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

### Option B — Run locally

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

A convenience script exists at `scripts/setup.sh` that runs the equivalent
of both steps above.

## Authentication flow

1. `POST /api/v1/auth/register` — create an account.
2. `POST /api/v1/auth/login` — returns a short-lived **access token** and a
   longer-lived **refresh token** (both JWTs).
3. The frontend attaches the access token to every request via an Axios
   interceptor and automatically refreshes it on a 401 response.
4. `GET /api/v1/users/me` — returns the current authenticated user.

## Companies (leads) API

Basic CRUD/listing is already wired up — it just has no data yet, since
no source implements real search/extraction logic:

- `GET /api/v1/companies` — list companies (filterable by `status`)
- `POST /api/v1/companies` — create a company record
- `GET /api/v1/companies/{id}` — fetch a single company
- `PATCH /api/v1/companies/{id}` — update a company (e.g. once a contact
  email is resolved)

## Database migrations

Migrations are managed with Alembic, wired to the SQLAlchemy models under
`backend/app/models/`.

```bash
cd backend
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

## What's intentionally NOT included

- Search/scraping/extraction logic for any of the four sources
  (`automation/sources/*` are structural placeholders only).
- Deduplication, enrichment, or email-resolution logic
  (`automation/handlers/*`, `automation/utils/*` are stubs).
- Playwright scripts/selectors.
- Billing, email verification, password reset, or social login flows.
- A production Kubernetes/CI setup (Dockerfiles are provided as a starting
  point only).

## Extending this template

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a fuller description
of how the pieces fit together, including the intended (not yet
implemented) lead-discovery data flow.
