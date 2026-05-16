import uuid

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.source import Source
from app.schemas.normalized_job import NormalizedJob


class JobRepository:
    """Job inserts (write path) and paginated reads (read path)."""

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

    async def list_jobs(
        self,
        tags: list[str] | None = None,
        salary_min: int | None = None,
        search: str | None = None,
        source: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        """Fetch a paginated, filtered list of active jobs.

        Args:
            tags: Return jobs that have ANY of these tags (PostgreSQL && operator).
            salary_min: Return jobs with salary_min >= this value.
            search: Full-text search across title, company, description.
            source: Filter by source name (e.g. 'remoteok').
            page: 1-based page number.
            page_size: Items per page.

        Returns:
            Tuple of (job list, total count matching filters).
        """
        conditions = [Job.is_active.is_(True)]

        if tags:
            conditions.append(Job.tags.overlap(tags))
        if salary_min is not None:
            conditions.append(Job.salary_min >= salary_min)
        if search:
            # Inline tsvector — works without a pre-computed column.
            # search_vector column gets pre-computed in a later migration for perf.
            lang = literal_column("'english'")
            text_body = func.concat_ws(" ", Job.title, Job.company, Job.description)
            conditions.append(
                func.to_tsvector(lang, text_body).op("@@")(
                    func.plainto_tsquery(lang, search)
                )
            )

        need_source_join = source is not None

        # --- count query (no pagination, no eager load) ---
        count_stmt = select(func.count()).select_from(Job)
        if need_source_join:
            count_stmt = count_stmt.join(Source, Job.source_id == Source.id).where(
                Source.name == source
            )
        count_stmt = count_stmt.where(*conditions)
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        # --- data query ---
        data_stmt = select(Job).options(selectinload(Job.source))
        if need_source_join:
            data_stmt = data_stmt.join(Source, Job.source_id == Source.id).where(
                Source.name == source
            )
        data_stmt = (
            data_stmt.where(*conditions)
            .order_by(Job.posted_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(data_stmt)
        return list(result.scalars().all()), total
