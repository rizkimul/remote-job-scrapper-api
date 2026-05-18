import uuid

import structlog
from sqlalchemy.exc import IntegrityError

from app.repositories.dedup_key_repository import DedupKeyRepository
from app.repositories.job_repository import JobRepository
from app.schemas.normalized_job import NormalizedJob

log = structlog.get_logger()


async def store_jobs(
    items: list[NormalizedJob],
    job_repo: JobRepository,
    dedup_repo: DedupKeyRepository,
    source_id: uuid.UUID,
    scrape_run_id: uuid.UUID,
) -> int:
    """Persist new jobs and their dedup keys to the database.

    Inserts Job + DedupKey for each item. Handles IntegrityError gracefully:
    if two workers race and one wins the dedup_keys unique constraint, the
    other silently skips that job rather than crashing the whole batch.

    Args:
        items: New items from the deduplicate stage (pre-filtered, but race conditions exist).
        job_repo: Repository for jobs table.
        dedup_repo: Repository for dedup_keys table.
        source_id: FK for jobs and dedup_keys rows.
        scrape_run_id: FK for jobs rows.

    Returns:
        Number of jobs actually stored.
    """
    stored = 0
    for item in items:
        try:
            job = await job_repo.create(item, source_id, scrape_run_id)
            await dedup_repo.create(
                key=item.dedup_hash,
                job_id=job.id,
                source_id=source_id,
            )
            stored += 1
        except IntegrityError:
            # Race condition: another worker stored this job between our dedup check and insert.
            await job_repo._session.rollback()
            log.warning("store_race_skip", source_url=item.source_url)

    log.info("store_complete", stored=stored, skipped=len(items) - stored)
    return stored
