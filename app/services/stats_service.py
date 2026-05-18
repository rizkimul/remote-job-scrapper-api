from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.scrape_run_repository import ScrapeRunRepository
from app.schemas.stats import (
    DailyJobCount,
    DailyJobStatsResponse,
    ScrapeStatsResponse,
    SourceScrapeStats,
)


class StatsService:
    """Read-only stats aggregation for admin endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self._scrape_run_repo = ScrapeRunRepository(session)

    async def get_scrape_stats(self) -> ScrapeStatsResponse:
        """Return per-source scrape success rates.

        Returns:
            ScrapeStatsResponse with one row per source.
        """
        rows = await self._scrape_run_repo.get_success_rate_by_source()
        sources = [
            SourceScrapeStats(
                source_name=name,
                total_runs=total,
                success_count=success,
                failed_count=failed,
                success_rate=round(success / total, 4) if total > 0 else 0.0,
            )
            for name, total, success, failed in rows
        ]
        return ScrapeStatsResponse(sources=sources)

    async def get_daily_job_stats(self, days: int = 7) -> DailyJobStatsResponse:
        """Return items stored per source per day for the last N days.

        Args:
            days: Lookback window in days.

        Returns:
            DailyJobStatsResponse with one row per (source, day).
        """
        rows = await self._scrape_run_repo.get_items_per_source_per_day(days=days)
        return DailyJobStatsResponse(
            days=days,
            rows=[
                DailyJobCount(source_name=name, date=day, items_stored=count)
                for name, day, count in rows
            ],
        )
