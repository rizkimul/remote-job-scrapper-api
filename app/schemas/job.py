import uuid
from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    """Public API response for a single job listing."""

    id: uuid.UUID
    title: str
    company: str
    description: str
    tags: list[str]
    salary_min: int | None
    salary_max: int | None
    currency: str
    posted_at: datetime
    source_url: str
    source_name: str
    created_at: datetime


class JobListResponse(BaseModel):
    """Paginated list of job listings."""

    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    pages: int
