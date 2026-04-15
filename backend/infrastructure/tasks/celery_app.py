"""
Celery application instance and beat schedule for SkyAlert.

Reads REDIS_URL from environment for both the broker and result backend.
The beat schedule runs scrape_all_searches every 5 minutes and
dispatch_pending_alerts every 2 minutes.
"""

import os

from celery import Celery
from celery.schedules import crontab


def _require_env(key: str) -> str:
    """
    Read a required environment variable or raise at startup.

    Args:
        key: The environment variable name.

    Returns:
        The variable's string value.

    Raises:
        RuntimeError: If the variable is not set.
    """
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Required environment variable '{key}' is not set.")
    return value


REDIS_URL: str = _require_env("REDIS_URL")

celery_app = Celery(
    "skyalert",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.infrastructure.tasks.scrape_tasks", "backend.infrastructure.tasks.notify_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # one task at a time per worker for scraping
)

celery_app.conf.beat_schedule = {
    "scrape-all-searches-every-5-minutes": {
        "task": "backend.infrastructure.tasks.scrape_tasks.scrape_all_searches",
        "schedule": crontab(minute="*/5"),
    },
    "dispatch-pending-alerts-every-2-minutes": {
        "task": "backend.infrastructure.tasks.notify_tasks.dispatch_pending_alerts",
        "schedule": crontab(minute="*/2"),
    },
}
