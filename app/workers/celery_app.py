from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "scraper_pipeline",
    include=["app.workers.tasks"],  # auto-register tasks without circular imports
)

celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    # Scrape each source every 6 hours; adjust per Source.scrape_interval_hours in Step 9
    "scrape-remoteok": {
        "task": "scrape_source",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": ("remoteok",),
    },
    # Digest email at 08:00 UTC daily (implemented in Step 8)
    "send-digest-daily": {
        "task": "send_digest",
        "schedule": crontab(hour=8, minute=0),
    },
    # Prune inactive jobs older than 90 days, Sunday 02:00 UTC
    "cleanup-stale-weekly": {
        "task": "cleanup_stale",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
    },
}
