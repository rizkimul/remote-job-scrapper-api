from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.job import JobListResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_service(session: Annotated[AsyncSession, Depends(get_db)]) -> JobService:
    """FastAPI dependency that returns a JobService bound to the request session."""
    return JobService(session)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    service: Annotated[JobService, Depends(get_job_service)],
    tags: Annotated[list[str] | None, Query(description="Filter jobs that have ANY of these tags")] = None,
    salary_min: Annotated[int | None, Query(ge=0, description="Minimum salary (job.salary_min >= value)")] = None,
    search: Annotated[str | None, Query(min_length=2, max_length=200, description="Full-text search")] = None,
    source: Annotated[str | None, Query(description="Filter by source name, e.g. 'remoteok'")] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> JobListResponse:
    """List remote job listings with optional filters and pagination.

    Returns:
        Paginated list of jobs matching the given filters.
    """
    return await service.list_jobs(
        tags=tags,
        salary_min=salary_min,
        search=search,
        source=source,
        page=page,
        page_size=page_size,
    )
