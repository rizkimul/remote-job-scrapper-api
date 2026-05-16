import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scrape_run import ScrapeRun, ScrapeRunStatus


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
