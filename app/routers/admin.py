from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.stats import DailyJobStatsResponse, ScrapeStatsResponse
from app.services.stats_service import StatsService

router = APIRouter(prefix="/admin", tags=["admin"])


def get_stats_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> StatsService:
    """FastAPI dependency that returns a StatsService bound to the request session."""
    return StatsService(session)


@router.get("/stats/scrape-runs", response_model=ScrapeStatsResponse)
async def scrape_run_stats(
    service: Annotated[StatsService, Depends(get_stats_service)],
) -> ScrapeStatsResponse:
    """Return scrape success rate per source.

    Counts only completed runs (SUCCESS or FAILED). In-progress runs excluded.

    Returns:
        One row per source with total/success/failed counts and success rate.
    """
    return await service.get_scrape_stats()


@router.get("/stats/jobs", response_model=DailyJobStatsResponse)
async def daily_job_stats(
    service: Annotated[StatsService, Depends(get_stats_service)],
    days: Annotated[
        int,
        Query(ge=1, le=90, description="Lookback window in days (max 90)"),
    ] = 7,
) -> DailyJobStatsResponse:
    """Return items stored per source per day over the last N days.

    Args:
        days: Number of past days to include (1–90, default 7).

    Returns:
        Rows ordered by date desc, then source name.
    """
    return await service.get_daily_job_stats(days=days)
