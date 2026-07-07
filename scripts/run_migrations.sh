#!/usr/bin/env bash
# Applies all pending Alembic migrations.
set -e
cd "$(dirname "$0")/../backend"
alembic upgrade head
