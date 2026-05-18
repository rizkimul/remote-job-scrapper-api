from datetime import date

from pydantic import BaseModel, Field


class SourceScrapeStats(BaseModel):
    """Scrape success rate for one source."""

    source_name: str
    total_runs: int
    success_count: int
    failed_count: int
    success_rate: float = Field(description="0.0–1.0")


class ScrapeStatsResponse(BaseModel):
    sources: list[SourceScrapeStats]


class DailyJobCount(BaseModel):
    """Items stored for one source on one day."""

    source_name: str
    date: date
    items_stored: int


class DailyJobStatsResponse(BaseModel):
    days: int
    rows: list[DailyJobCount]
