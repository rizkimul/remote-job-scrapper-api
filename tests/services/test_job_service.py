import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.job_service import JobService

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_job(**kwargs) -> MagicMock:
    job = MagicMock()
    job.id = uuid.uuid4()
    job.title = "Python Dev"
    job.company = "Acme Corp"
    job.description = "Remote Python role"
    job.tags = ["python", "fastapi"]
    job.salary_min = 80000
    job.salary_max = 120000
    job.currency = "USD"
    job.posted_at = _NOW
    job.source_url = "https://remoteok.com/jobs/1"
    job.source.name = "remoteok"
    job.created_at = _NOW
    for k, v in kwargs.items():
        setattr(job, k, v)
    return job


async def test_list_jobs_returns_items_and_total():
    service = JobService(MagicMock())
    job = _make_job()

    with patch.object(service._repo, "list_jobs", new=AsyncMock(return_value=([job], 1))):
        result = await service.list_jobs()

    assert result.total == 1
    assert len(result.items) == 1


async def test_list_jobs_calculates_pages():
    service = JobService(MagicMock())

    with patch.object(service._repo, "list_jobs", new=AsyncMock(return_value=([], 45))):
        result = await service.list_jobs(page_size=20)

    assert result.pages == 3  # ceil(45/20)


async def test_list_jobs_empty_gives_zero_pages():
    service = JobService(MagicMock())

    with patch.object(service._repo, "list_jobs", new=AsyncMock(return_value=([], 0))):
        result = await service.list_jobs()

    assert result.total == 0
    assert result.pages == 0
    assert result.items == []


async def test_list_jobs_forwards_all_filters_to_repo():
    service = JobService(MagicMock())
    mock_repo = AsyncMock(return_value=([], 0))

    with patch.object(service._repo, "list_jobs", new=mock_repo):
        await service.list_jobs(
            tags=["python"],
            salary_min=80000,
            search="engineer",
            source="remoteok",
            page=2,
            page_size=10,
        )

    mock_repo.assert_called_once_with(
        tags=["python"],
        salary_min=80000,
        search="engineer",
        source="remoteok",
        page=2,
        page_size=10,
    )


async def test_list_jobs_maps_job_fields_to_response():
    service = JobService(MagicMock())
    job = _make_job()

    with patch.object(service._repo, "list_jobs", new=AsyncMock(return_value=([job], 1))):
        result = await service.list_jobs()

    item = result.items[0]
    assert item.title == "Python Dev"
    assert item.company == "Acme Corp"
    assert item.source_name == "remoteok"
    assert item.salary_min == 80000
    assert item.salary_max == 120000
    assert item.tags == ["python", "fastapi"]
    assert item.created_at == _NOW


async def test_list_jobs_page_metadata_propagated():
    service = JobService(MagicMock())

    with patch.object(service._repo, "list_jobs", new=AsyncMock(return_value=([], 100))):
        result = await service.list_jobs(page=3, page_size=20)

    assert result.page == 3
    assert result.page_size == 20
    assert result.pages == 5  # ceil(100/20)
