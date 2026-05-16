import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.normalized_job import NormalizedJob


class JobRepository:
    """Handles job inserts. Reads live in the router/service layer (Step 6)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        item: NormalizedJob,
        source_id: uuid.UUID,
        scrape_run_id: uuid.UUID,
    ) -> Job:
        """Insert a normalized job into the jobs table.

        search_vector is left NULL here. It will be populated by the
        tsvector update trigger added in a future migration.

        Args:
            item: Normalized job data from the pipeline.
            source_id: FK to sources table.
            scrape_run_id: FK to the ScrapeRun that produced this job.

        Returns:
            Persisted Job ORM instance.
        """
        job = Job(
            title=item.title,
            company=item.company,
            description=item.description,
            tags=item.tags,
            salary_min=item.salary_min,
            salary_max=item.salary_max,
            currency=item.currency,
            posted_at=item.posted_at,
            source_url=item.source_url,
            source_id=source_id,
            scrape_run_id=scrape_run_id,
        )
        self._session.add(job)
        await self._session.flush()
        return job
