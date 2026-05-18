from datetime import date
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from httpx import ASGITransport

from app.main import create_app
from app.routers.admin import get_stats_service
from app.schemas.stats import (
    DailyJobCount,
    DailyJobStatsResponse,
    ScrapeStatsResponse,
    SourceScrapeStats,
)

_TODAY = date(2026, 5, 18)


def _make_scrape_stats(*sources: tuple) -> ScrapeStatsResponse:
    """Build a ScrapeStatsResponse from (name, total, success, failed) tuples."""
    return ScrapeStatsResponse(
        sources=[
            SourceScrapeStats(
                source_name=name,
                total_runs=total,
                success_count=success,
                failed_count=failed,
                success_rate=round(success / total, 4) if total > 0 else 0.0,
            )
            for name, total, success, failed in sources
        ]
    )


def _make_daily_stats(days: int = 7, *rows: tuple) -> DailyJobStatsResponse:
    return DailyJobStatsResponse(
        days=days,
        rows=[
            DailyJobCount(source_name=name, date=d, items_stored=count)
            for name, d, count in rows
        ],
    )


def _mock_service(
    scrape_stats: ScrapeStatsResponse | None = None,
    daily_stats: DailyJobStatsResponse | None = None,
) -> MagicMock:
    svc = MagicMock()
    svc.get_scrape_stats = AsyncMock(
        return_value=scrape_stats or _make_scrape_stats(("remoteok", 10, 9, 1))
    )
    svc.get_daily_job_stats = AsyncMock(
        return_value=daily_stats or _make_daily_stats(7, ("remoteok", _TODAY, 12))
    )
    return svc


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_scrape_run_stats_returns_200(app, client):
    app.dependency_overrides[get_stats_service] = lambda: _mock_service()

    async with client as c:
        response = await c.get("/admin/stats/scrape-runs")

    assert response.status_code == 200


async def test_scrape_run_stats_response_shape(app, client):
    stats = _make_scrape_stats(("remoteok", 10, 9, 1), ("remotive", 5, 5, 0))
    app.dependency_overrides[get_stats_service] = lambda: _mock_service(scrape_stats=stats)

    async with client as c:
        response = await c.get("/admin/stats/scrape-runs")

    body = response.json()
    assert "sources" in body
    assert len(body["sources"]) == 2
    first = body["sources"][0]
    assert first["source_name"] == "remoteok"
    assert first["total_runs"] == 10
    assert first["success_count"] == 9
    assert first["failed_count"] == 1
    assert first["success_rate"] == 0.9


async def test_scrape_run_stats_empty_sources(app, client):
    app.dependency_overrides[get_stats_service] = lambda: _mock_service(
        scrape_stats=ScrapeStatsResponse(sources=[])
    )

    async with client as c:
        response = await c.get("/admin/stats/scrape-runs")

    assert response.status_code == 200
    assert response.json()["sources"] == []


async def test_daily_job_stats_returns_200(app, client):
    app.dependency_overrides[get_stats_service] = lambda: _mock_service()

    async with client as c:
        response = await c.get("/admin/stats/jobs")

    assert response.status_code == 200


async def test_daily_job_stats_default_days_is_7(app, client):
    mock_svc = _mock_service()
    app.dependency_overrides[get_stats_service] = lambda: mock_svc

    async with client as c:
        await c.get("/admin/stats/jobs")

    mock_svc.get_daily_job_stats.assert_called_once_with(days=7)


async def test_daily_job_stats_custom_days_forwarded(app, client):
    mock_svc = _mock_service()
    app.dependency_overrides[get_stats_service] = lambda: mock_svc

    async with client as c:
        await c.get("/admin/stats/jobs?days=30")

    mock_svc.get_daily_job_stats.assert_called_once_with(days=30)


async def test_daily_job_stats_response_shape(app, client):
    daily = _make_daily_stats(7, ("remoteok", _TODAY, 12), ("remotive", _TODAY, 34))
    app.dependency_overrides[get_stats_service] = lambda: _mock_service(daily_stats=daily)

    async with client as c:
        response = await c.get("/admin/stats/jobs")

    body = response.json()
    assert body["days"] == 7
    assert len(body["rows"]) == 2
    assert body["rows"][0]["source_name"] == "remoteok"
    assert body["rows"][0]["items_stored"] == 12
    assert body["rows"][0]["date"] == str(_TODAY)


async def test_daily_job_stats_days_above_max_422(app, client):
    app.dependency_overrides[get_stats_service] = lambda: _mock_service()

    async with client as c:
        response = await c.get("/admin/stats/jobs?days=91")

    assert response.status_code == 422


async def test_daily_job_stats_days_zero_422(app, client):
    app.dependency_overrides[get_stats_service] = lambda: _mock_service()

    async with client as c:
        response = await c.get("/admin/stats/jobs?days=0")

    assert response.status_code == 422
