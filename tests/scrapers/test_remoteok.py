import json
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from app.core.exceptions import BlockedError, ParseError, RateLimitError
from app.scrapers.remoteok.scraper import RemoteOKScraper

_API_URL = "https://remoteok.com/api"

# Shared fixture data
_METADATA = {"legal": "..."}
_JOB_1 = {
    "slug": "senior-python-dev-acme-123",
    "company": "Acme Corp",
    "position": "Senior Python Dev",
    "description": "<p>Great job</p>",
    "tags": ["python", "remote", "fastapi"],
    "salary_min": "80000",
    "salary_max": "120000",
    "url": "https://remoteok.com/remote-jobs/senior-python-dev-acme-123",
    "epoch": "1700000000",
}
_JOB_2 = {
    "slug": "frontend-dev-beta-456",
    "company": "Beta Inc",
    "position": "Frontend Developer",
    "description": "",
    "tags": [],
    "salary_min": None,
    "salary_max": None,
    "url": "",
    "epoch": "1700001000",
}


@pytest.fixture
def scraper() -> RemoteOKScraper:
    client = httpx.AsyncClient()
    return RemoteOKScraper(client=client)


@respx.mock
async def test_scrape_returns_job_items(scraper: RemoteOKScraper) -> None:
    respx.get(_API_URL).mock(
        return_value=httpx.Response(200, json=[_METADATA, _JOB_1, _JOB_2])
    )
    # Bypass polite delay in tests
    scraper._polite_delay = AsyncMock()  # type: ignore[method-assign]

    items = await scraper.scrape()

    assert len(items) == 2
    assert items[0].title == "Senior Python Dev"
    assert items[0].company == "Acme Corp"
    assert items[0].tags == ["python", "remote", "fastapi"]
    assert items[0].salary_min == 80000
    assert items[0].salary_max == 120000
    assert items[0].source_name == "remoteok"


@respx.mock
async def test_scrape_skips_metadata_at_index_zero(scraper: RemoteOKScraper) -> None:
    """First element (metadata) must never appear as a job."""
    respx.get(_API_URL).mock(
        return_value=httpx.Response(200, json=[_METADATA, _JOB_1])
    )
    scraper._polite_delay = AsyncMock()  # type: ignore[method-assign]

    items = await scraper.scrape()

    assert len(items) == 1
    assert items[0].company == "Acme Corp"


@respx.mock
async def test_fetch_raises_rate_limit_on_429(scraper: RemoteOKScraper) -> None:
    respx.get(_API_URL).mock(return_value=httpx.Response(429))

    with pytest.raises(RateLimitError):
        await scraper.fetch()


@respx.mock
async def test_fetch_raises_blocked_on_403(scraper: RemoteOKScraper) -> None:
    respx.get(_API_URL).mock(return_value=httpx.Response(403))

    with pytest.raises(BlockedError):
        await scraper.fetch()


@respx.mock
async def test_parse_raises_on_invalid_json(scraper: RemoteOKScraper) -> None:
    with pytest.raises(ParseError):
        await scraper.parse(b"not valid json {{{{")


@respx.mock
async def test_parse_skips_malformed_entry(scraper: RemoteOKScraper) -> None:
    """Entry missing 'position' (title) is skipped, rest of batch succeeds."""
    malformed = {"slug": "bad-entry", "company": "X"}  # no 'position'
    respx.get(_API_URL).mock(
        return_value=httpx.Response(200, json=[_METADATA, malformed, _JOB_1])
    )
    scraper._polite_delay = AsyncMock()  # type: ignore[method-assign]

    items = await scraper.scrape()

    assert len(items) == 1
    assert items[0].title == "Senior Python Dev"


@respx.mock
async def test_parse_falls_back_to_slug_url_when_url_empty(
    scraper: RemoteOKScraper,
) -> None:
    """When 'url' field is empty, source_url built from slug."""
    scraper._polite_delay = AsyncMock()  # type: ignore[method-assign]
    respx.get(_API_URL).mock(
        return_value=httpx.Response(200, json=[_METADATA, _JOB_2])
    )

    items = await scraper.scrape()

    assert "frontend-dev-beta-456" in items[0].source_url


@respx.mock
async def test_parse_handles_empty_tags(scraper: RemoteOKScraper) -> None:
    scraper._polite_delay = AsyncMock()  # type: ignore[method-assign]
    respx.get(_API_URL).mock(
        return_value=httpx.Response(200, json=[_METADATA, _JOB_2])
    )

    items = await scraper.scrape()

    assert items[0].tags == []
