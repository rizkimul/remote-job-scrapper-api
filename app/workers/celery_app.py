from celery import Celery

from app.core.config import settings

celery_app = Celery("scraper_pipeline")
celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
