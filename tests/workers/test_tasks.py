import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.scrape_run import ScrapeRunStatus
from app.schemas.pipeline import PipelineResult
from app.workers.tasks import _run_scrape_source, _run_send_digest, cleanup_stale

_RUN_ID = uuid.uuid4()

_SUCCESS_RESULT = PipelineResult(
    source_name="remoteok",
    scrape_run_id=_RUN_ID,
    status=ScrapeRunStatus.SUCCESS,
    items_found=10,
    items_stored=8,
)

_FAILED_RESULT = PipelineResult(
    source_name="remoteok",
    scrape_run_id=_RUN_ID,
    status=ScrapeRunStatus.FAILED,
    items_found=0,
    items_stored=0,
    error_message="network down",
)


async def test_run_scrape_source_returns_serialisable_dict():
    mock_service = MagicMock()
    mock_service.run = AsyncMock(return_value=_SUCCESS_RESULT)

    with (
        patch("app.workers.tasks.AsyncSessionLocal") as mock_session_cls,
        patch("app.workers.tasks.PipelineService", return_value=mock_service),
    ):
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await _run_scrape_source("remoteok")

    assert result["status"] == "success"
    assert result["items_found"] == 10
    assert result["items_stored"] == 8
    assert result["source_name"] == "remoteok"


async def test_run_scrape_source_failed_pipeline_returns_dict_not_raises():
    """PipelineService.run() returns FAILED result — task should return, not raise."""
    mock_service = MagicMock()
    mock_service.run = AsyncMock(return_value=_FAILED_RESULT)

    with (
        patch("app.workers.tasks.AsyncSessionLocal") as mock_session_cls,
        patch("app.workers.tasks.PipelineService", return_value=mock_service),
    ):
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await _run_scrape_source("remoteok")

    assert result["status"] == "failed"
    assert result["error_message"] == "network down"
    assert result["items_stored"] == 0


async def test_run_scrape_source_passes_source_name_to_service():
    mock_service = MagicMock()
    mock_service.run = AsyncMock(return_value=_SUCCESS_RESULT)

    with (
        patch("app.workers.tasks.AsyncSessionLocal") as mock_session_cls,
        patch("app.workers.tasks.PipelineService", return_value=mock_service),
    ):
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _run_scrape_source("remoteok")

    mock_service.run.assert_called_once_with("remoteok")


async def test_run_send_digest_returns_serialisable_dict():
    mock_service = MagicMock()
    mock_service.send_all_digests = AsyncMock(
        return_value=MagicMock(
            model_dump=MagicMock(
                return_value={"subscriptions_processed": 2, "emails_sent": 1}
            )
        )
    )

    with (
        patch("app.workers.tasks.AsyncSessionLocal") as mock_session_cls,
        patch("app.workers.tasks.SubscriptionService", return_value=mock_service),
    ):
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await _run_send_digest()

    assert result["subscriptions_processed"] == 2
    assert result["emails_sent"] == 1


def test_cleanup_stale_stub_returns_not_implemented():
    result = cleanup_stale()
    assert result["status"] == "not_implemented"
