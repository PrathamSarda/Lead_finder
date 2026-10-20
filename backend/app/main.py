"""
FastAPI application entrypoint.
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

backend_dir = Path(__file__).resolve().parent.parent
workspace_dir = backend_dir.parent
for d in (backend_dir, workspace_dir):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.app.api.v1.api import api_router
    from backend.app.core.config import settings
    from backend.app.scheduler.scheduler import start_scheduler, shutdown_scheduler
except ImportError:
    from app.api.v1.api import api_router
    from app.core.config import settings
    from app.scheduler.scheduler import start_scheduler, shutdown_scheduler



@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "status": "running"}
