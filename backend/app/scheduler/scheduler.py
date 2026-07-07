"""
APScheduler setup.

This wires up a background scheduler that starts/stops with the FastAPI
app lifecycle. No jobs are registered here — add them in `register_jobs`
as the product requires scheduled work (e.g. periodic syncs, cleanups).
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def register_jobs() -> None:
    """Register scheduled jobs here. Left empty in the starter template."""
    pass


def start_scheduler() -> None:
    register_jobs()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
