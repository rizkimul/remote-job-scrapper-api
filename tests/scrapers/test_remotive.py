from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from app.core.exceptions import BlockedError, ParseError, RateLimitError
from app.scrapers.remotive.scraper import RemotiveScraper

_API_URL = "https://remotive.com/api/remote-jobs?category=software-dev"

_JOB_1 = {
    "id": 1,
    "title": "Senior Python Dev",
    "company_name": "Acme Corp",
    "description": "<p>Great remote job</p>",
    "tags": ["python", "fastapi"],
    "salary": "",
    "url": "https://remotive.com/remote-jobs/software-dev/senior-python-dev-1",
    "publication_date": "2026-01-01T00:00:00",
}

_JOB_2 = {
    "id": 2,
    "title": "Frontend Engineer",
    "company_name": "Beta Inc",
    "description": "",
    "tags": [],
    "salary": "$100k",
    "url": "https://remotive.com/remote-jobs/software-dev/frontend-engineer-2",
    "publication_date": "2026-01-02T10:30:00+00:00",
}

_RESPONSE = {"jobs": [_JOB_1, _JOB_2], "job-count": 2}


@pytest.fixture
def scraper() -> RemotiveScraper:
    return RemotiveScraper(client=httpx.AsyncClient())


@respx.mock
async def test_scrape_returns_job_items(scraper: RemotiveScraper) -> None:
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=_RESPONSE))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert len(items) == 2
    assert items[0].title == "Senior Python Dev"
    assert items[0].company == "Acme Corp"
    assert items[0].source_name == "remotive"
    assert items[0].tags == ["python", "fastapi"]


@respx.mock
async def test_parse_maps_description_as_raw_html(scraper: RemotiveScraper) -> None:
    """Description kept as HTML — normalize stage strips it later."""
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=_RESPONSE))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert items[0].description == "<p>Great remote job</p>"


@respx.mock
async def test_parse_handles_utc_date_without_timezone(scraper: RemotiveScraper) -> None:
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=_RESPONSE))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert items[0].posted_at.tzinfo is not None


@respx.mock
async def test_parse_handles_date_with_timezone(scraper: RemotiveScraper) -> None:
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=_RESPONSE))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert items[1].posted_at.tzinfo is not None


@respx.mock
async def test_parse_salary_fields_are_none(scraper: RemotiveScraper) -> None:
    """Remotive salary is unstructured text — we skip parsing, store None."""
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=_RESPONSE))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert items[0].salary_min is None
    assert items[0].salary_max is None


@respx.mock
async def test_parse_skips_malformed_entry(scraper: RemotiveScraper) -> None:
    malformed = {"id": 99}  # missing title, company_name, url, publication_date
    payload = {"jobs": [malformed, _JOB_1], "job-count": 2}
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=payload))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert len(items) == 1
    assert items[0].title == "Senior Python Dev"


@respx.mock
async def test_parse_returns_empty_when_jobs_key_missing(scraper: RemotiveScraper) -> None:
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json={}))
    scraper._polite_delay = AsyncMock()

    items = await scraper.scrape()

    assert items == []


@respx.mock
async def test_fetch_raises_rate_limit_on_429(scraper: RemotiveScraper) -> None:
    respx.get(_API_URL).mock(return_value=httpx.Response(429))

    with pytest.raises(RateLimitError):
        await scraper.fetch()


@respx.mock
async def test_fetch_raises_blocked_on_403(scraper: RemotiveScraper) -> None:
    respx.get(_API_URL).mock(return_value=httpx.Response(403))

    with pytest.raises(BlockedError):
        await scraper.fetch()


@respx.mock
async def test_parse_raises_on_invalid_json(scraper: RemotiveScraper) -> None:
    with pytest.raises(ParseError):
        await scraper.parse(b"not json {{")
