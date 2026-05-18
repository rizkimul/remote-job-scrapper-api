import math
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from httpx import ASGITransport

from app.main import create_app
from app.routers.jobs import get_job_service
from app.schemas.job import JobListResponse, JobResponse

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_JOB_ID = uuid.uuid4()


def _make_job_response(**overrides) -> JobResponse:
    defaults = dict(
        id=_JOB_ID,
        title="Senior Python Dev",
        company="Acme Corp",
        description="Great job",
        tags=["python", "fastapi"],
        salary_min=80000,
        salary_max=120000,
        currency="USD",
        posted_at=_NOW,
        source_url="https://remoteok.com/jobs/1",
        source_name="remoteok",
        created_at=_NOW,
    )
    return JobResponse(**{**defaults, **overrides})


def _make_list_response(items: list[JobResponse], total: int = None) -> JobListResponse:
    t = total if total is not None else len(items)
    pages = math.ceil(t / 20) if t > 0 else 0
    return JobListResponse(items=items, total=t, page=1, page_size=20, pages=pages)


def _mock_service(return_value: JobListResponse) -> MagicMock:
    svc = MagicMock()
    svc.list_jobs = AsyncMock(return_value=return_value)
    return svc


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_list_jobs_returns_200_with_empty_list(app, client):
    empty = _make_list_response([], total=0)
    app.dependency_overrides[get_job_service] = lambda: _mock_service(empty)

    async with client as c:
        response = await c.get("/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["pages"] == 0


async def test_list_jobs_returns_jobs_with_pagination_metadata(app, client):
    job = _make_job_response()
    payload = _make_list_response([job], total=50)
    app.dependency_overrides[get_job_service] = lambda: _mock_service(payload)

    async with client as c:
        response = await c.get("/jobs?page=1&page_size=20")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["total"] == 50
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["items"][0]["title"] == "Senior Python Dev"
    assert body["items"][0]["source_name"] == "remoteok"


async def test_list_jobs_passes_tags_filter_to_service(app, client):
    mock_svc = _mock_service(_make_list_response([]))
    app.dependency_overrides[get_job_service] = lambda: mock_svc

    async with client as c:
        await c.get("/jobs?tags=python&tags=fastapi")

    mock_svc.list_jobs.assert_called_once()
    kwargs = mock_svc.list_jobs.call_args.kwargs
    assert kwargs["tags"] == ["python", "fastapi"]


async def test_list_jobs_passes_salary_min_to_service(app, client):
    mock_svc = _mock_service(_make_list_response([]))
    app.dependency_overrides[get_job_service] = lambda: mock_svc

    async with client as c:
        await c.get("/jobs?salary_min=80000")

    kwargs = mock_svc.list_jobs.call_args.kwargs
    assert kwargs["salary_min"] == 80000


async def test_list_jobs_passes_search_to_service(app, client):
    mock_svc = _mock_service(_make_list_response([]))
    app.dependency_overrides[get_job_service] = lambda: mock_svc

    async with client as c:
        await c.get("/jobs?search=python+backend")

    kwargs = mock_svc.list_jobs.call_args.kwargs
    assert kwargs["search"] == "python backend"


async def test_list_jobs_passes_source_to_service(app, client):
    mock_svc = _mock_service(_make_list_response([]))
    app.dependency_overrides[get_job_service] = lambda: mock_svc

    async with client as c:
        await c.get("/jobs?source=remoteok")

    kwargs = mock_svc.list_jobs.call_args.kwargs
    assert kwargs["source"] == "remoteok"


async def test_list_jobs_rejects_page_size_over_100(app, client):
    app.dependency_overrides[get_job_service] = lambda: _mock_service(_make_list_response([]))

    async with client as c:
        response = await c.get("/jobs?page_size=101")

    assert response.status_code == 422


async def test_list_jobs_rejects_page_zero(app, client):
    app.dependency_overrides[get_job_service] = lambda: _mock_service(_make_list_response([]))

    async with client as c:
        response = await c.get("/jobs?page=0")

    assert response.status_code == 422


async def test_list_jobs_rejects_search_too_short(app, client):
    app.dependency_overrides[get_job_service] = lambda: _mock_service(_make_list_response([]))

    async with client as c:
        response = await c.get("/jobs?search=x")

    assert response.status_code == 422


async def test_list_jobs_rejects_negative_salary_min(app, client):
    app.dependency_overrides[get_job_service] = lambda: _mock_service(_make_list_response([]))

    async with client as c:
        response = await c.get("/jobs?salary_min=-1")

    assert response.status_code == 422
