import json
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.exceptions import BlockedError, ParseError, RateLimitError, ScrapeError
from app.schemas.scraper import RawJobItem
from app.scrapers.base import BaseScraper

_API_URL = "https://remoteok.com/api"


class RemoteOKScraper(BaseScraper):
    """Scraper for remoteok.com public JSON API.

    Endpoint: GET https://remoteok.com/api
    No auth required. First element in response array is metadata — skipped.
    """

    source_name = "remoteok"
    base_url = "https://remoteok.com"

    async def fetch(self) -> bytes:
        """GET the RemoteOK API and return raw response bytes.

        Maps HTTP error codes to ScrapeError subclasses so BaseScraper retry
        logic only sees our exception hierarchy, not httpx internals.
        """
        try:
            response = await self._client.get(
                _API_URL,
                headers={"User-Agent": settings.scrape_user_agent},
                follow_redirects=True,
            )
        except httpx.NetworkError as exc:
            raise ScrapeError(
                f"network error fetching remoteok: {exc}", code="network_error"
            ) from exc

        if response.status_code == 429:
            raise RateLimitError("RemoteOK rate limit hit", code="rate_limit")
        if response.status_code in (401, 403):
            raise BlockedError("RemoteOK blocked our request", code="blocked")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ScrapeError(
                f"unexpected HTTP {response.status_code}", code="http_error"
            ) from exc

        return response.content

    async def parse(self, raw: bytes) -> list[RawJobItem]:
        """Parse JSON array from RemoteOK API into RawJobItem list.

        Skips index 0 (metadata object). Skips individual entries that are
        missing required fields rather than failing the entire batch.
        """
        try:
            data: list[dict] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParseError(
                f"RemoteOK JSON decode failed: {exc}", code="parse_error"
            ) from exc

        items: list[RawJobItem] = []
        for entry in data[1:]:  # index 0 is a metadata object, not a job
            try:
                items.append(self._map_entry(entry))
            except (KeyError, ValueError, TypeError):
                self._log.warning(
                    "skip_malformed_entry",
                    slug=entry.get("slug"),
                    reason="missing or invalid required field",
                )

        return items

    def _map_entry(self, entry: dict) -> RawJobItem:
        posted_at = (
            datetime.fromtimestamp(int(entry["epoch"]), tz=timezone.utc)
            if entry.get("epoch")
            else datetime.now(tz=timezone.utc)
        )

        salary_min: int | None = None
        salary_max: int | None = None
        if raw_min := entry.get("salary_min"):
            try:
                salary_min = int(raw_min)
            except (ValueError, TypeError):
                pass
        if raw_max := entry.get("salary_max"):
            try:
                salary_max = int(raw_max)
            except (ValueError, TypeError):
                pass

        source_url: str = entry.get("url") or (
            f"https://remoteok.com/remote-jobs/{entry['slug']}"
        )

        return RawJobItem(
            title=entry["position"],
            company=entry["company"],
            description=entry.get("description", ""),
            tags=entry.get("tags") or [],
            salary_min=salary_min,
            salary_max=salary_max,
            currency="USD",
            posted_at=posted_at,
            source_url=source_url,
            source_name=self.source_name,
        )
