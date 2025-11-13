"""Background scheduler for monthly credit resets."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from ..core.database import SessionLocal
from ..services.monthly_reset_service import run_monthly_reset

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")


async def _execute_monthly_reset() -> None:
    session = SessionLocal()
    try:
        summary = run_monthly_reset(session, current_time=datetime.now(timezone.utc))
        session.commit()
        logger.info("monthly reset completed: %s", summary)
    except Exception:  # pragma: no cover - safeguard for background job
        session.rollback()
        logger.exception("monthly reset job failed")
        raise
    finally:
        session.close()


@_scheduler.scheduled_job("cron", day="1", hour=0, minute=5, id="monthly_reset", misfire_grace_time=3600)
async def _scheduled_job() -> None:
    await _execute_monthly_reset()


def register_scheduler(app: FastAPI) -> None:
    """Attach APScheduler lifecycle hooks to the FastAPI app."""

    @app.on_event("startup")
    async def start_scheduler() -> None:
        if not _scheduler.running:
            _scheduler.start()
            logger.info("monthly reset scheduler started")

    @app.on_event("shutdown")
    async def shutdown_scheduler() -> None:
        if _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("monthly reset scheduler stopped")


def run_reset_once(current_time: datetime | None = None) -> dict[str, int]:
    """Convenience helper to run the reset synchronously for manual testing."""

    session = SessionLocal()
    try:
        summary = run_monthly_reset(session, current_time=current_time)
        session.commit()
        return summary
    finally:
        session.close()
