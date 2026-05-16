import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError
from app.models.scrape_run import ScrapeRun, ScrapeRunStatus
from app.models.source import Source
from app.schemas.normalized_job import NormalizedJob
from app.schemas.scraper import RawJobItem
from app.services.pipeline_service import PipelineService

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
_SOURCE_ID = uuid.uuid4()
_RUN_ID = uuid.uuid4()


def _make_source() -> Source:
    s = MagicMock(spec=Source)
    s.id = _SOURCE_ID
    s.name = "remoteok"
    return s


def _make_run() -> ScrapeRun:
    r = MagicMock(spec=ScrapeRun)
    r.id = _RUN_ID
    return r


def _make_raw_item() -> RawJobItem:
    return RawJobItem(
        title="Python Dev",
        company="Acme",
        description="<p>desc</p>",
        tags=["python"],
        salary_min=None,
        salary_max=None,
        currency="USD",
        posted_at=_NOW,
        source_url="https://remoteok.com/jobs/1",
        source_name="remoteok",
    )


def _make_normalized_item() -> NormalizedJob:
    return NormalizedJob(
        title="Python Dev",
        company="Acme",
        description="desc",
        tags=["python"],
        salary_min=None,
        salary_max=None,
        currency="USD",
        posted_at=_NOW,
        source_url="https://remoteok.com/jobs/1",
        source_name="remoteok",
        dedup_hash="a" * 64,
    )


def _mock_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _make_scraper_registry(raw_items: list[RawJobItem]) -> dict:
    """Build a fake registry where the scraper returns controlled raw_items."""
    mock_scraper = MagicMock()
    mock_scraper.scrape = AsyncMock(return_value=raw_items)
    mock_scraper._polite_delay = AsyncMock()
    scraper_cls = MagicMock(return_value=mock_scraper)
    return {"remoteok": scraper_cls}


def _make_failing_registry(error: Exception) -> dict:
    """Build a fake registry where the scraper raises an error."""
    mock_scraper = MagicMock()
    mock_scraper.scrape = AsyncMock(side_effect=error)
    scraper_cls = MagicMock(return_value=mock_scraper)
    return {"remoteok": scraper_cls}


async def test_run_raises_if_source_not_found():
    session = _mock_session()
    service = PipelineService(session=session)

    with patch.object(service._source_repo, "get_by_name", new=AsyncMock(return_value=None)):
        with pytest.raises(AppError, match="not found"):
            await service.run("unknown_source")


async def test_run_returns_success_result():
    session = _mock_session()
    service = PipelineService(session=session)

    raw_items = [_make_raw_item()]
    normalized = [_make_normalized_item()]

    with (
        patch.object(service._source_repo, "get_by_name", new=AsyncMock(return_value=_make_source())),
        patch.object(service._run_repo, "create", new=AsyncMock(return_value=_make_run())),
        patch.object(service._run_repo, "complete", new=AsyncMock()),
        patch("app.services.pipeline_service._SCRAPER_REGISTRY", _make_scraper_registry(raw_items)),
        patch("app.services.pipeline_service.normalize_items", return_value=normalized),
        patch("app.services.pipeline_service.deduplicate_items", new=AsyncMock(return_value=normalized)),
        patch("app.services.pipeline_service.store_jobs", new=AsyncMock(return_value=1)),
    ):
        result = await service.run("remoteok")

    assert result.status == ScrapeRunStatus.SUCCESS
    assert result.items_found == 1
    assert result.items_stored == 1
    assert result.source_name == "remoteok"
    assert result.scrape_run_id == _RUN_ID


async def test_run_marks_failed_on_scraper_error():
    session = _mock_session()
    service = PipelineService(session=session)

    with (
        patch.object(service._source_repo, "get_by_name", new=AsyncMock(return_value=_make_source())),
        patch.object(service._run_repo, "create", new=AsyncMock(return_value=_make_run())),
        patch.object(service._run_repo, "complete", new=AsyncMock()),
        patch(
            "app.services.pipeline_service._SCRAPER_REGISTRY",
            _make_failing_registry(RuntimeError("network down")),
        ),
    ):
        result = await service.run("remoteok")

    assert result.status == ScrapeRunStatus.FAILED
    assert result.error_message == "network down"
    assert result.items_stored == 0


async def test_run_commits_on_success():
    session = _mock_session()
    service = PipelineService(session=session)

    normalized = [_make_normalized_item()]

    with (
        patch.object(service._source_repo, "get_by_name", new=AsyncMock(return_value=_make_source())),
        patch.object(service._run_repo, "create", new=AsyncMock(return_value=_make_run())),
        patch.object(service._run_repo, "complete", new=AsyncMock()),
        patch("app.services.pipeline_service._SCRAPER_REGISTRY", _make_scraper_registry([_make_raw_item()])),
        patch("app.services.pipeline_service.normalize_items", return_value=normalized),
        patch("app.services.pipeline_service.deduplicate_items", new=AsyncMock(return_value=normalized)),
        patch("app.services.pipeline_service.store_jobs", new=AsyncMock(return_value=1)),
    ):
        await service.run("remoteok")

    assert session.commit.call_count == 2  # once after create, once after store


async def test_run_rollback_on_failure():
    session = _mock_session()
    service = PipelineService(session=session)

    with (
        patch.object(service._source_repo, "get_by_name", new=AsyncMock(return_value=_make_source())),
        patch.object(service._run_repo, "create", new=AsyncMock(return_value=_make_run())),
        patch.object(service._run_repo, "complete", new=AsyncMock()),
        patch(
            "app.services.pipeline_service._SCRAPER_REGISTRY",
            _make_failing_registry(RuntimeError("boom")),
        ),
    ):
        await service.run("remoteok")

    session.rollback.assert_called_once()
