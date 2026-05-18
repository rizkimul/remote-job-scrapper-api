import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from httpx import ASGITransport

from app.main import create_app
from app.routers.subscriptions import get_subscription_service
from app.schemas.subscription import SubscriptionResponse

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_sub_response(**kwargs) -> SubscriptionResponse:
    defaults = dict(
        id=uuid.uuid4(),
        email="test@example.com",
        tags_filter=None,
        min_salary=None,
        is_active=True,
        created_at=_NOW,
    )
    return SubscriptionResponse(**{**defaults, **kwargs})


def _mock_service(subscribe_return=None, unsubscribe_return=True) -> MagicMock:
    svc = MagicMock()
    svc.subscribe = AsyncMock(return_value=subscribe_return or _make_sub_response())
    svc.unsubscribe = AsyncMock(return_value=unsubscribe_return)
    return svc


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_subscribe_returns_201(app, client):
    app.dependency_overrides[get_subscription_service] = lambda: _mock_service()

    async with client as c:
        response = await c.post("/subscriptions", json={"email": "test@example.com"})

    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"


async def test_subscribe_with_filters(app, client):
    mock_svc = _mock_service()
    app.dependency_overrides[get_subscription_service] = lambda: mock_svc

    async with client as c:
        await c.post(
            "/subscriptions",
            json={"email": "test@example.com", "tags_filter": ["python"], "min_salary": 80000},
        )

    mock_svc.subscribe.assert_called_once_with(
        email="test@example.com",
        tags_filter=["python"],
        min_salary=80000,
    )


async def test_subscribe_normalises_email_to_lowercase(app, client):
    mock_svc = _mock_service()
    app.dependency_overrides[get_subscription_service] = lambda: mock_svc

    async with client as c:
        await c.post("/subscriptions", json={"email": "TEST@EXAMPLE.COM"})

    call_email = mock_svc.subscribe.call_args.kwargs["email"]
    assert call_email == "test@example.com"


async def test_subscribe_rejects_invalid_email(app, client):
    app.dependency_overrides[get_subscription_service] = lambda: _mock_service()

    async with client as c:
        response = await c.post("/subscriptions", json={"email": "not-an-email"})

    assert response.status_code == 422


async def test_subscribe_rejects_negative_min_salary(app, client):
    app.dependency_overrides[get_subscription_service] = lambda: _mock_service()

    async with client as c:
        response = await c.post(
            "/subscriptions", json={"email": "test@example.com", "min_salary": -1}
        )

    assert response.status_code == 422


async def test_unsubscribe_returns_204_when_found(app, client):
    app.dependency_overrides[get_subscription_service] = lambda: _mock_service(
        unsubscribe_return=True
    )

    async with client as c:
        response = await c.delete("/subscriptions/test@example.com")

    assert response.status_code == 204


async def test_unsubscribe_returns_404_when_not_found(app, client):
    app.dependency_overrides[get_subscription_service] = lambda: _mock_service(
        unsubscribe_return=False
    )

    async with client as c:
        response = await c.delete("/subscriptions/ghost@example.com")

    assert response.status_code == 404
