import asyncio
import random
from abc import ABC, abstractmethod

import httpx
import structlog

from app.core.config import settings
from app.core.exceptions import BlockedError, ScrapeError
from app.schemas.scraper import RawJobItem

log = structlog.get_logger()


class BaseScraper(ABC):
    """Abstract base for all source scrapers.

    Subclasses implement fetch() and parse(). The scrape() template method
    orchestrates polite delay → retry-wrapped fetch → parse → structured log.
    """

    source_name: str  # set as class var in each concrete scraper
    base_url: str

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._log = log.bind(source=self.source_name)

    @abstractmethod
    async def fetch(self) -> bytes:
        """Fetch raw bytes from the source. Raise ScrapeError subclasses on failure."""
        ...

    @abstractmethod
    async def parse(self, raw: bytes) -> list[RawJobItem]:
        """Parse raw response into RawJobItem list."""
        ...

    async def scrape(self) -> list[RawJobItem]:
        """Template: polite delay → fetch (with retry) → parse → log."""
        await self._polite_delay()
        raw = await self._fetch_with_retry()
        items = await self.parse(raw)
        self._log.info("scrape_complete", items_found=len(items))
        return items

    async def _fetch_with_retry(self, max_attempts: int = 3) -> bytes:
        last_exc: ScrapeError | None = None
        for attempt in range(max_attempts):
            try:
                return await self.fetch()
            except BlockedError:
                raise  # blocking is not transient, never retry
            except ScrapeError as exc:
                last_exc = exc
                if attempt == max_attempts - 1:
                    break
                # exponential backoff with jitter: 1s, 2-3s, 4-5s
                delay = (2**attempt) + random.uniform(0, 1)
                self._log.warning(
                    "fetch_retry",
                    attempt=attempt + 1,
                    retry_in_s=round(delay, 2),
                    error=str(exc),
                )
                await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def _polite_delay(self) -> None:
        delay = random.uniform(settings.scrape_delay_min, settings.scrape_delay_max)
        self._log.debug("polite_delay", seconds=round(delay, 2))
        await asyncio.sleep(delay)
