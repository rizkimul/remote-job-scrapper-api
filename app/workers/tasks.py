import asyncio

import structlog

from app.core.db import AsyncSessionLocal
from app.services.pipeline_service import PipelineService
from app.workers.celery_app import celery_app

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Internal async helpers — extracted so tests can call them without a Celery worker
# ---------------------------------------------------------------------------


async def _run_scrape_source(source_name: str) -> dict:
    """Run the full pipeline for one source. Returns serialisable result dict."""
    async with AsyncSessionLocal() as session:
        service = PipelineService(session=session)
        result = await service.run(source_name)
        return result.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, name="scrape_source", max_retries=3)
def scrape_source(self, source_name: str) -> dict:
    """Trigger the scrape pipeline for a single source.

    Celery tasks are synchronous; asyncio.run() bridges to async PipelineService.
    PipelineService.run() handles its own errors and returns a FAILED result
    without raising, so retries here only fire on infrastructure failures
    (e.g. DB unreachable before a session can be created).

    Args:
        source_name: Name of the source to scrape (must exist in sources table).

    Returns:
        Serialised PipelineResult dict.
    """
    bound_log = log.bind(source=source_name, attempt=self.request.retries + 1)
    bound_log.info("task_start")

    try:
        result = asyncio.run(_run_scrape_source(source_name))
        bound_log.info("task_complete", status=result.get("status"))
        return result
    except Exception as exc:
        countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        bound_log.error("task_retry", error=str(exc), retry_in_s=countdown)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(name="send_digest")
def send_digest() -> dict:
    """Send daily digest emails to subscribers. Implemented in Step 8.

    Returns:
        Stub result.
    """
    log.info("send_digest_stub")
    return {"status": "not_implemented"}


@celery_app.task(name="cleanup_stale")
def cleanup_stale() -> dict:
    """Mark jobs older than 90 days as inactive. Implemented in Step 9.

    Returns:
        Stub result.
    """
    log.info("cleanup_stale_stub")
    return {"status": "not_implemented"}
