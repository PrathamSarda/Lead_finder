"""
Health check endpoint — useful for load balancers, uptime checks, and CI.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}
