from datetime import datetime

from pydantic import BaseModel


class RawJobItem(BaseModel):
    """Output contract for all scrapers. Input to the normalize pipeline stage."""

    title: str
    company: str
    description: str
    tags: list[str] = []
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str = "USD"
    posted_at: datetime
    source_url: str
    source_name: str
