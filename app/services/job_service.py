import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobListResponse, JobResponse


class JobService:
    """Read path for job listings. Maps ORM objects to API response schemas."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = JobRepository(session)

    async def list_jobs(
        self,
        tags: list[str] | None = None,
        salary_min: int | None = None,
        search: str | None = None,
        source: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> JobListResponse:
        """Fetch paginated, filtered jobs and return API-ready response.

        Args:
            tags: ANY-match tag filter.
            salary_min: Minimum salary filter.
            search: Full-text search string.
            source: Source name filter.
            page: 1-based page number.
            page_size: Items per page (max 100).

        Returns:
            Paginated JobListResponse with metadata.
        """
        jobs, total = await self._repo.list_jobs(
            tags=tags,
            salary_min=salary_min,
            search=search,
            source=source,
            page=page,
            page_size=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 0
        return JobListResponse(
            items=[_map_job(job) for job in jobs],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


def _map_job(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        description=job.description,
        tags=job.tags,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        currency=job.currency,
        posted_at=job.posted_at,
        source_url=job.source_url,
        source_name=job.source.name,  # from selectinload in repo
        created_at=job.created_at,
    )
