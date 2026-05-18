import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scrape_run import ScrapeRun, ScrapeRunStatus
from app.models.source import Source


class ScrapeRunRepository:
    """Manages ScrapeRun lifecycle: create on start, update on completion."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, source_id: uuid.UUID) -> ScrapeRun:
        """Insert a new ScrapeRun with status RUNNING.

        Args:
            source_id: UUID of the source being scraped.

        Returns:
            Persisted ScrapeRun instance.
        """
        run = ScrapeRun(
            source_id=source_id,
            status=ScrapeRunStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
        )
        self._session.add(run)
        await self._session.flush()  # get id without committing
        return run

    async def complete(
        self,
        run_id: uuid.UUID,
        status: ScrapeRunStatus,
        items_found: int,
        items_stored: int,
        error_message: str | None = None,
    ) -> None:
        """Update a ScrapeRun with final status and item counts.

        Args:
            run_id: UUID of the run to update.
            status: SUCCESS or FAILED.
            items_found: Total items returned by the scraper.
            items_stored: Items written to jobs table (excluding dupes).
            error_message: Error detail if status is FAILED.
        """
        run = await self._session.get(ScrapeRun, run_id)
        if run is None:
            return
        run.status = status
        run.ended_at = datetime.now(tz=timezone.utc)
        run.items_found = items_found
        run.items_stored = items_stored
        run.error_message = error_message
        await self._session.flush()

    async def get_success_rate_by_source(
        self,
    ) -> list[tuple[str, int, int, int]]:
        """Return (source_name, total_runs, success_count, failed_count) per source.

        Excludes RUNNING rows — they have no final status yet.

        Returns:
            List of tuples ordered by source name.
        """
        stmt = (
            select(
                Source.name,
                func.count().label("total_runs"),
                func.sum(
                    case((ScrapeRun.status == ScrapeRunStatus.SUCCESS, 1), else_=0)
                ).label("success_count"),
                func.sum(
                    case((ScrapeRun.status == ScrapeRunStatus.FAILED, 1), else_=0)
                ).label("failed_count"),
            )
            .join(Source, ScrapeRun.source_id == Source.id)
            .where(ScrapeRun.status != ScrapeRunStatus.RUNNING)
            .group_by(Source.name)
            .order_by(Source.name)
        )
        rows = (await self._session.execute(stmt)).all()
        return [(r.name, r.total_runs, r.success_count, r.failed_count) for r in rows]

    async def get_items_per_source_per_day(
        self,
        days: int = 7,
    ) -> list[tuple[str, date, int]]:
        """Return (source_name, date, items_stored) for the last N days.

        Args:
            days: Number of past days to include (default 7).

        Returns:
            List of tuples ordered by date desc, source name.
        """
        since = datetime.now(tz=timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                Source.name,
                func.date_trunc("day", ScrapeRun.ended_at).label("day"),
                func.sum(ScrapeRun.items_stored).label("items_stored"),
            )
            .join(Source, ScrapeRun.source_id == Source.id)
            .where(
                ScrapeRun.status == ScrapeRunStatus.SUCCESS,
                ScrapeRun.ended_at >= since,
            )
            .group_by(Source.name, func.date_trunc("day", ScrapeRun.ended_at))
            .order_by(func.date_trunc("day", ScrapeRun.ended_at).desc(), Source.name)
        )
        rows = (await self._session.execute(stmt)).all()
        return [(r.name, r.day.date(), int(r.items_stored)) for r in rows]
