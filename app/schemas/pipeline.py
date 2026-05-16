import uuid

from pydantic import BaseModel

from app.models.scrape_run import ScrapeRunStatus


class PipelineResult(BaseModel):
    """Returned by PipelineService.run() after a scrape pipeline completes."""

    source_name: str
    scrape_run_id: uuid.UUID
    status: ScrapeRunStatus
    items_found: int
    items_stored: int
    error_message: str | None = None
