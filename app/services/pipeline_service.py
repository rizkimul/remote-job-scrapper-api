import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.scrape_run import ScrapeRunStatus
from app.pipelines.deduplicate import deduplicate_items
from app.pipelines.normalize import normalize_items
from app.pipelines.store import store_jobs
from app.repositories.dedup_key_repository import DedupKeyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.scrape_run_repository import ScrapeRunRepository
from app.repositories.source_repository import SourceRepository
from app.scrapers.remoteok.scraper import RemoteOKScraper
from app.schemas.pipeline import PipelineResult

log = structlog.get_logger()

_SCRAPER_REGISTRY: dict[str, type] = {
    "remoteok": RemoteOKScraper,
}


class PipelineService:
    """Orchestrates the full scrape pipeline for a single source.

    Owns the ScrapeRun lifecycle: creates it on start, updates to SUCCESS
    or FAILED on completion. Celery tasks call this service.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._source_repo = SourceRepository(session)
        self._run_repo = ScrapeRunRepository(session)
        self._job_repo = JobRepository(session)
        self._dedup_repo = DedupKeyRepository(session)

    async def run(self, source_name: str) -> PipelineResult:
        """Execute the full pipeline: extract → normalize → deduplicate → store.

        Args:
            source_name: Name of the source to scrape (must exist in sources table).

        Returns:
            PipelineResult with run status and item counts.

        Raises:
            AppError: If the source is not found in the database.
        """
        bound_log = log.bind(source=source_name)

        source = await self._source_repo.get_by_name(source_name)
        if source is None:
            raise AppError(f"Source '{source_name}' not found", code="source_not_found")

        scrape_run = await self._run_repo.create(source_id=source.id)
        await self._session.commit()

        bound_log = bound_log.bind(scrape_run_id=str(scrape_run.id))
        bound_log.info("pipeline_start")

        items_found = 0
        items_stored = 0

        try:
            scraper_cls = _SCRAPER_REGISTRY.get(source_name)
            if scraper_cls is None:
                raise AppError(
                    f"No scraper registered for '{source_name}'",
                    code="scraper_not_found",
                )

            async with httpx.AsyncClient() as client:
                scraper = scraper_cls(client=client)
                raw_items = await scraper.scrape()

            items_found = len(raw_items)
            bound_log.info("extract_complete", items_found=items_found)

            normalized = normalize_items(raw_items)
            new_items = await deduplicate_items(normalized, self._dedup_repo)
            items_stored = await store_jobs(
                new_items,
                self._job_repo,
                self._dedup_repo,
                source_id=source.id,
                scrape_run_id=scrape_run.id,
            )

            await self._run_repo.complete(
                run_id=scrape_run.id,
                status=ScrapeRunStatus.SUCCESS,
                items_found=items_found,
                items_stored=items_stored,
            )
            await self._session.commit()
            bound_log.info("pipeline_complete", items_stored=items_stored)

        except Exception as exc:
            await self._session.rollback()
            error_msg = str(exc)
            await self._run_repo.complete(
                run_id=scrape_run.id,
                status=ScrapeRunStatus.FAILED,
                items_found=items_found,
                items_stored=0,
                error_message=error_msg,
            )
            await self._session.commit()
            bound_log.error("pipeline_failed", error=error_msg)
            return PipelineResult(
                source_name=source_name,
                scrape_run_id=scrape_run.id,
                status=ScrapeRunStatus.FAILED,
                items_found=items_found,
                items_stored=0,
                error_message=error_msg,
            )

        return PipelineResult(
            source_name=source_name,
            scrape_run_id=scrape_run.id,
            status=ScrapeRunStatus.SUCCESS,
            items_found=items_found,
            items_stored=items_stored,
        )
