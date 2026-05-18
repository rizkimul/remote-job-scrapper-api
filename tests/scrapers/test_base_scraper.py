from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.exceptions import BlockedError, RateLimitError, ScrapeError
from app.schemas.scraper import RawJobItem
from app.scrapers.base import BaseScraper


class _TestScraper(BaseScraper):
    """Minimal concrete scraper for testing BaseScraper internals."""

    source_name = "test_source"
    base_url = "https://test.example.com"

    async def fetch(self) -> bytes:
        return b"[]"

    async def parse(self, raw: bytes) -> list[RawJobItem]:
        return []


@pytest.fixture
def scraper() -> _TestScraper:
    return _TestScraper(client=httpx.AsyncClient())


async def test_fetch_with_retry_succeeds_first_attempt(scraper: _TestScraper) -> None:
    scraper.fetch = AsyncMock(return_value=b"data")  # type: ignore[method-assign]

    result = await scraper._fetch_with_retry()

    assert result == b"data"
    scraper.fetch.assert_called_once()


async def test_fetch_with_retry_raises_blocked_error_without_retry(
    scraper: _TestScraper,
) -> None:
    """BlockedError is permanent — must not retry."""
    scraper.fetch = AsyncMock(side_effect=BlockedError("ip blocked"))  # type: ignore[method-assign]

    with pytest.raises(BlockedError):
        await scraper._fetch_with_retry()

    # Only one attempt — no retry on blocked
    scraper.fetch.assert_called_once()


async def test_fetch_with_retry_retries_on_scrape_error(scraper: _TestScraper) -> None:
    """ScrapeError on first attempt triggers retry; second attempt succeeds."""
    scraper.fetch = AsyncMock(  # type: ignore[method-assign]
        side_effect=[RateLimitError("429"), b"ok"]
    )

    with patch("app.scrapers.base.asyncio.sleep", new=AsyncMock()):
        result = await scraper._fetch_with_retry()

    assert result == b"ok"
    assert scraper.fetch.call_count == 2


async def test_fetch_with_retry_raises_after_max_attempts(scraper: _TestScraper) -> None:
    """Exhausting all retries raises the last ScrapeError."""
    scraper.fetch = AsyncMock(side_effect=RateLimitError("always 429"))  # type: ignore[method-assign]

    with patch("app.scrapers.base.asyncio.sleep", new=AsyncMock()), pytest.raises(ScrapeError):
        await scraper._fetch_with_retry(max_attempts=3)

    assert scraper.fetch.call_count == 3


async def test_fetch_with_retry_exponential_backoff_delays(scraper: _TestScraper) -> None:
    """Each retry uses a longer delay (exponential backoff)."""
    scraper.fetch = AsyncMock(side_effect=RateLimitError("rate limited"))  # type: ignore[method-assign]

    sleep_calls: list[float] = []

    async def capture_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    with (
        patch("app.scrapers.base.asyncio.sleep", side_effect=capture_sleep),
        pytest.raises(ScrapeError),
    ):
        await scraper._fetch_with_retry(max_attempts=3)

    assert len(sleep_calls) == 2  # 3 attempts → 2 sleeps between them
    # Second sleep must be longer than first (exponential)
    assert sleep_calls[1] > sleep_calls[0]


async def test_polite_delay_calls_sleep(scraper: _TestScraper) -> None:
    with patch("app.scrapers.base.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        await scraper._polite_delay()

    mock_sleep.assert_called_once()
    delay = mock_sleep.call_args[0][0]
    assert delay >= 0
