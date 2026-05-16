from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from app.core.exceptions import BlockedError, RateLimitError
from app.scrapers.wwr.scraper import WWRScraper

_LISTING_URL = "https://weworkremotely.com/remote-jobs/search?term=developer"

# Minimal HTML fixture matching the selectors in WWRScraper._map_article()
_HTML_ONE_JOB = b"""
<html><body>
<section class="jobs">
  <article class="feature">
    <a href="/remote-jobs/1-senior-python-dev-acme-corp">
      <span class="company">Acme Corp</span>
      <span class="title">Senior Python Dev</span>
      <span class="region">Worldwide</span>
      <ul class="tags">
        <li>Python</li>
        <li>FastAPI</li>
      </ul>
    </a>
  </article>
</section>
</body></html>
"""

_HTML_TWO_JOBS = b"""
<html><body>
<section class="jobs">
  <article class="feature">
    <a href="/remote-jobs/1-senior-python-dev-acme-corp">
      <span class="company">Acme Corp</span>
      <span class="title">Senior Python Dev</span>
      <ul class="tags"><li>Python</li></ul>
    </a>
  </article>
  <article class="feature">
    <a href="/remote-jobs/2-frontend-engineer-beta-inc">
      <span class="company">Beta Inc</span>
      <span class="title">Frontend Engineer</span>
      <ul class="tags"><li>React</li><li>TypeScript</li></ul>
    </a>
  </article>
</section>
</body></html>
"""

_HTML_MALFORMED_ARTICLE = b"""
<html><body>
<section class="jobs">
  <article class="feature">
    <!-- no .company or .title spans -->
    <a href="/remote-jobs/broken">broken</a>
  </article>
  <article class="feature">
    <a href="/remote-jobs/1-good-job">
      <span class="company">Good Corp</span>
      <span class="title">Good Job</span>
    </a>
  </article>
</section>
</body></html>
"""

_HTML_NO_JOBS = b"<html><body><section class='jobs'></section></body></html>"


@pytest.fixture
def scraper() -> WWRScraper:
    return WWRScraper(client=httpx.AsyncClient())


@respx.mock
async def test_scrape_returns_job_items(scraper: WWRScraper) -> None:
    respx.get(_LISTING_URL).mock(return_value=httpx.Response(200, content=_HTML_ONE_JOB))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert len(items) == 1
    assert items[0].title == "Senior Python Dev"
    assert items[0].company == "Acme Corp"
    assert items[0].source_name == "wwr"


@respx.mock
async def test_scrape_parses_multiple_jobs(scraper: WWRScraper) -> None:
    respx.get(_LISTING_URL).mock(return_value=httpx.Response(200, content=_HTML_TWO_JOBS))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert len(items) == 2
    assert items[1].company == "Beta Inc"


@respx.mock
async def test_scrape_builds_full_source_url(scraper: WWRScraper) -> None:
    respx.get(_LISTING_URL).mock(return_value=httpx.Response(200, content=_HTML_ONE_JOB))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert items[0].source_url == "https://weworkremotely.com/remote-jobs/1-senior-python-dev-acme-corp"


@respx.mock
async def test_scrape_parses_tags(scraper: WWRScraper) -> None:
    respx.get(_LISTING_URL).mock(return_value=httpx.Response(200, content=_HTML_ONE_JOB))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert items[0].tags == ["Python", "FastAPI"]


@respx.mock
async def test_scrape_description_is_empty_string(scraper: WWRScraper) -> None:
    """Listing page has no description — stored as empty, not None."""
    respx.get(_LISTING_URL).mock(return_value=httpx.Response(200, content=_HTML_ONE_JOB))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert items[0].description == ""


@respx.mock
async def test_scrape_skips_malformed_article_keeps_valid(scraper: WWRScraper) -> None:
    respx.get(_LISTING_URL).mock(
        return_value=httpx.Response(200, content=_HTML_MALFORMED_ARTICLE)
    )
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert len(items) == 1
    assert items[0].title == "Good Job"


@respx.mock
async def test_scrape_returns_empty_when_no_articles(scraper: WWRScraper) -> None:
    respx.get(_LISTING_URL).mock(return_value=httpx.Response(200, content=_HTML_NO_JOBS))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert items == []


@respx.mock
async def test_fetch_raises_rate_limit_on_429(scraper: WWRScraper) -> None:
    respx.get(_LISTING_URL).mock(return_value=httpx.Response(429))

    with pytest.raises(RateLimitError):
        await scraper.fetch()


@respx.mock
async def test_fetch_raises_blocked_on_403(scraper: WWRScraper) -> None:
    respx.get(_LISTING_URL).mock(return_value=httpx.Response(403))

    with pytest.raises(BlockedError):
        await scraper.fetch()
