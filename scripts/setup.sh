#!/usr/bin/env bash
# Bootstraps local development: installs backend + frontend dependencies
# and copies .env.example files if .env files don't exist yet.
set -e

echo "==> Setting up backend"
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
deactivate
cd ..

echo "==> Setting up frontend"
cd frontend
npm install
[ -f .env ] || cp .env.example .env
cd ..

echo "==> Done. Next steps:"
echo "    1. Start PostgreSQL (docker compose up -d db)"
echo "    2. Run migrations (cd backend && alembic upgrade head)"
echo "    3. Start the backend (cd backend && uvicorn app.main:app --reload)"
echo "    4. Start the frontend (cd frontend && npm run dev)"
