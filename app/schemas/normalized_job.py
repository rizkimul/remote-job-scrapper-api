from datetime import datetime

from pydantic import BaseModel


class NormalizedJob(BaseModel):
    """Pipeline-internal DTO. Output of normalize stage, input to deduplicate and store."""

    title: str
    company: str
    description: str  # HTML stripped by normalize stage
    tags: list[str]   # lowercased, deduplicated
    salary_min: int | None
    salary_max: int | None
    currency: str
    posted_at: datetime
    source_url: str
    source_name: str
    dedup_hash: str   # SHA-256 of company|title|description[:200], computed by normalize
