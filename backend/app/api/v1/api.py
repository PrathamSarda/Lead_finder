"""
Aggregates all v1 routers into a single APIRouter mounted in main.py.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, companies, health, users

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])

# Placeholder for future domain routers as the pipeline grows, e.g.:
# from app.api.v1.endpoints import searches
# api_router.include_router(searches.router, prefix="/searches", tags=["searches"])
