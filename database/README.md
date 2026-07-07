# Database

This project uses PostgreSQL, managed via SQLAlchemy models (`backend/app/models/`)
and Alembic migrations (`backend/alembic/`).

## Local development

A `docker-compose.yml` service named `db` provisions a local PostgreSQL instance.
Connection details are controlled via `DATABASE_URL` in `backend/.env`.

## Migrations

Run from the `backend/` directory:

```bash
# Create a new migration after changing models
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head
```

## Seed data

Add seed scripts under `scripts/` and document them here as they're introduced.
This starter template ships without seed data.
