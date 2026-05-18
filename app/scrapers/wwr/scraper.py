from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup, Tag

from app.core.config import settings
from app.core.exceptions import BlockedError, ParseError, RateLimitError, ScrapeError
from app.schemas.scraper import RawJobItem
from app.scrapers.base import BaseScraper

_LISTING_URL = "https://weworkremotely.com/remote-jobs/search?term=developer"


class WWRScraper(BaseScraper):
    """Scraper for weworkremotely.com listing page (static HTML).

    Fetches the developer job search page. Description is not available on
    the listing page — we store empty string and rely on title + company for
    dedup hash. Detail page fetching is intentionally skipped to avoid N
    extra HTTP calls per scrape run.
    """

    source_name = "wwr"
    base_url = "https://weworkremotely.com"

    async def fetch(self) -> bytes:
        """GET the WWR search listing page and return raw HTML bytes."""
        try:
            response = await self._client.get(
                _LISTING_URL,
                headers={"User-Agent": settings.scrape_user_agent},
                follow_redirects=True,
            )
        except httpx.NetworkError as exc:
            raise ScrapeError(
                f"network error fetching wwr: {exc}", code="network_error"
            ) from exc

        if response.status_code == 429:
            raise RateLimitError("WWR rate limit hit", code="rate_limit")
        if response.status_code in (401, 403):
            raise BlockedError("WWR blocked our request", code="blocked")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ScrapeError(
                f"unexpected HTTP {response.status_code}", code="http_error"
            ) from exc

        return response.content

    async def parse(self, raw: bytes) -> list[RawJobItem]:
        """Parse WWR HTML listing into RawJobItem list.

        Targets: section.jobs > article.feature elements.
        Skips malformed articles rather than failing the whole batch.
        """
        try:
            soup = BeautifulSoup(raw, "html.parser")
        except Exception as exc:
            raise ParseError(f"WWR HTML parse failed: {exc}", code="parse_error") from exc

        articles = soup.select("section.jobs article.feature")
        if not articles:
            self._log.warning("no_articles_found", hint="WWR HTML structure may have changed")

        items: list[RawJobItem] = []
        for article in articles:
            try:
                items.append(self._map_article(article))
            except (AttributeError, TypeError, KeyError):
                self._log.warning("skip_malformed_article", html=str(article)[:100])

        return items

    def _map_article(self, article: Tag) -> RawJobItem:
        link = article.find("a")
        if not link:
            raise AttributeError("no <a> tag in article")

        href: str = str(link.get("href", "")) if hasattr(link, "get") else ""
        source_url = f"{self.base_url}{href}" if href.startswith("/") else href

        company_tag = article.select_one(".company")
        title_tag = article.select_one(".title")

        if not company_tag or not title_tag:
            raise AttributeError("missing .company or .title in article")

        company = company_tag.get_text(strip=True)
        title = title_tag.get_text(strip=True)
        tags = [t for li in article.select("ul.tags li") if (t := li.get_text(strip=True))]

        return RawJobItem(
            title=title,
            company=company,
            description="",  # not available on listing page
            tags=tags,
            salary_min=None,
            salary_max=None,
            currency="USD",
            posted_at=datetime.now(tz=UTC),
            source_url=source_url,
            source_name=self.source_name,
        )
