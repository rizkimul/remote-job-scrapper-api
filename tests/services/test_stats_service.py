from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.stats_service import StatsService


def _mock_session() -> MagicMock:
    return MagicMock()


async def test_get_scrape_stats_calculates_success_rate():
    session = _mock_session()
    service = StatsService(session)

    rows = [("remoteok", 10, 8, 2)]
    with patch.object(
        service._scrape_run_repo,
        "get_success_rate_by_source",
        new=AsyncMock(return_value=rows),
    ):
        result = await service.get_scrape_stats()

    assert len(result.sources) == 1
    s = result.sources[0]
    assert s.source_name == "remoteok"
    assert s.total_runs == 10
    assert s.success_count == 8
    assert s.failed_count == 2
    assert s.success_rate == 0.8


async def test_get_scrape_stats_zero_total_guard():
    session = _mock_session()
    service = StatsService(session)

    # total=0 should not raise ZeroDivisionError
    rows = [("remoteok", 0, 0, 0)]
    with patch.object(
        service._scrape_run_repo,
        "get_success_rate_by_source",
        new=AsyncMock(return_value=rows),
    ):
        result = await service.get_scrape_stats()

    assert result.sources[0].success_rate == 0.0


async def test_get_scrape_stats_all_success():
    session = _mock_session()
    service = StatsService(session)

    rows = [("remotive", 5, 5, 0)]
    with patch.object(
        service._scrape_run_repo,
        "get_success_rate_by_source",
        new=AsyncMock(return_value=rows),
    ):
        result = await service.get_scrape_stats()

    assert result.sources[0].success_rate == 1.0


async def test_get_scrape_stats_multiple_sources():
    session = _mock_session()
    service = StatsService(session)

    rows = [
        ("remoteok", 10, 9, 1),
        ("remotive", 20, 20, 0),
        ("wwr", 4, 2, 2),
    ]
    with patch.object(
        service._scrape_run_repo,
        "get_success_rate_by_source",
        new=AsyncMock(return_value=rows),
    ):
        result = await service.get_scrape_stats()

    assert len(result.sources) == 3
    names = [s.source_name for s in result.sources]
    assert names == ["remoteok", "remotive", "wwr"]


async def test_get_scrape_stats_empty():
    session = _mock_session()
    service = StatsService(session)

    with patch.object(
        service._scrape_run_repo,
        "get_success_rate_by_source",
        new=AsyncMock(return_value=[]),
    ):
        result = await service.get_scrape_stats()

    assert result.sources == []


async def test_get_daily_job_stats_returns_rows():
    session = _mock_session()
    service = StatsService(session)

    today = date(2026, 5, 18)
    rows = [("remoteok", today, 12), ("remotive", today, 34)]
    with patch.object(
        service._scrape_run_repo,
        "get_items_per_source_per_day",
        new=AsyncMock(return_value=rows),
    ):
        result = await service.get_daily_job_stats(days=7)

    assert result.days == 7
    assert len(result.rows) == 2
    assert result.rows[0].source_name == "remoteok"
    assert result.rows[0].date == today
    assert result.rows[0].items_stored == 12


async def test_get_daily_job_stats_forwards_days_param():
    session = _mock_session()
    service = StatsService(session)

    mock_repo = AsyncMock(return_value=[])
    with patch.object(service._scrape_run_repo, "get_items_per_source_per_day", new=mock_repo):
        await service.get_daily_job_stats(days=30)

    mock_repo.assert_called_once_with(days=30)


async def test_get_daily_job_stats_empty():
    session = _mock_session()
    service = StatsService(session)

    with patch.object(
        service._scrape_run_repo,
        "get_items_per_source_per_day",
        new=AsyncMock(return_value=[]),
    ):
        result = await service.get_daily_job_stats()

    assert result.rows == []
