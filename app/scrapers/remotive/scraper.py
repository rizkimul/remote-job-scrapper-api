import json
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.exceptions import BlockedError, ParseError, RateLimitError, ScrapeError
from app.schemas.scraper import RawJobItem
from app.scrapers.base import BaseScraper

_API_URL = "https://remotive.com/api/remote-jobs?category=software-dev"


class RemotiveScraper(BaseScraper):
    """Scraper for remotive.com public JSON API.

    Endpoint: GET https://remotive.com/api/remote-jobs?category=software-dev
    Response shape: {"jobs": [...], "job-count": N}
    Description field contains raw HTML — stripped by the normalize stage.
    """

    source_name = "remotive"
    base_url = "https://remotive.com"

    async def fetch(self) -> bytes:
        """GET the Remotive API and return raw response bytes."""
        try:
            response = await self._client.get(
                _API_URL,
                headers={"User-Agent": settings.scrape_user_agent},
                follow_redirects=True,
            )
        except httpx.NetworkError as exc:
            raise ScrapeError(
                f"network error fetching remotive: {exc}", code="network_error"
            ) from exc

        if response.status_code == 429:
            raise RateLimitError("Remotive rate limit hit", code="rate_limit")
        if response.status_code in (401, 403):
            raise BlockedError("Remotive blocked our request", code="blocked")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ScrapeError(
                f"unexpected HTTP {response.status_code}", code="http_error"
            ) from exc

        return response.content

    async def parse(self, raw: bytes) -> list[RawJobItem]:
        """Parse Remotive JSON into RawJobItem list.

        Skips malformed entries rather than failing the whole batch.
        """
        try:
            data: dict = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParseError(
                f"Remotive JSON decode failed: {exc}", code="parse_error"
            ) from exc

        items: list[RawJobItem] = []
        for entry in data.get("jobs", []):
            try:
                items.append(self._map_entry(entry))
            except (KeyError, ValueError, TypeError):
                self._log.warning(
                    "skip_malformed_entry",
                    job_id=entry.get("id"),
                    reason="missing or invalid required field",
                )

        return items

    def _map_entry(self, entry: dict) -> RawJobItem:
        posted_at = _parse_date(entry["publication_date"])

        return RawJobItem(
            title=entry["title"],
            company=entry["company_name"],
            description=entry.get("description", ""),  # HTML — normalize stage strips it
            tags=entry.get("tags") or [],
            salary_min=None,   # Remotive salary field is unstructured text; skip parsing
            salary_max=None,
            currency="USD",
            posted_at=posted_at,
            source_url=entry["url"],
            source_name=self.source_name,
        )


def _parse_date(date_str: str) -> datetime:
    """Parse ISO 8601 date string. Assumes UTC if no timezone present."""
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
