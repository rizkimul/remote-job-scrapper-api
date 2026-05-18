import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.digest_subscription import DigestSubscription
from app.models.job import Job
from app.schemas.subscription import DigestResult
from app.services.subscription_service import SubscriptionService

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_SUB_ID = uuid.uuid4()
_JOB_ID = uuid.uuid4()


def _make_sub(**kwargs) -> DigestSubscription:
    sub = MagicMock(spec=DigestSubscription)
    sub.id = _SUB_ID
    sub.email = "test@example.com"
    sub.tags_filter = None
    sub.min_salary = None
    sub.is_active = True
    sub.created_at = _NOW
    for k, v in kwargs.items():
        setattr(sub, k, v)
    return sub


def _make_job(job_id: uuid.UUID = _JOB_ID) -> Job:
    job = MagicMock(spec=Job)
    job.id = job_id
    job.title = "Python Dev"
    job.company = "Acme"
    job.tags = ["python"]
    job.salary_min = None
    job.salary_max = None
    job.currency = "USD"
    job.source_url = "https://remoteok.com/jobs/1"
    return job


def _mock_session() -> MagicMock:
    s = MagicMock()
    s.commit = AsyncMock()
    s.rollback = AsyncMock()
    return s


async def test_subscribe_returns_subscription_response():
    session = _mock_session()
    service = SubscriptionService(session=session)
    sub = _make_sub()

    with patch.object(service._sub_repo, "create_or_reactivate", new=AsyncMock(return_value=sub)):
        result = await service.subscribe("test@example.com", None, None)

    assert result.email == "test@example.com"
    assert result.is_active is True
    session.commit.assert_called_once()


async def test_unsubscribe_returns_true_when_found():
    session = _mock_session()
    service = SubscriptionService(session=session)

    with patch.object(service._sub_repo, "deactivate", new=AsyncMock(return_value=True)):
        result = await service.unsubscribe("test@example.com")

    assert result is True
    session.commit.assert_called_once()


async def test_unsubscribe_returns_false_when_not_found():
    session = _mock_session()
    service = SubscriptionService(session=session)

    with patch.object(service._sub_repo, "deactivate", new=AsyncMock(return_value=False)):
        result = await service.unsubscribe("ghost@example.com")

    assert result is False
    session.commit.assert_not_called()


async def test_send_all_digests_skips_when_no_new_jobs():
    session = _mock_session()
    service = SubscriptionService(session=session)
    sub = _make_sub()

    with (
        patch.object(service._sub_repo, "get_all_active", new=AsyncMock(return_value=[sub])),
        patch.object(service._job_repo, "list_jobs", new=AsyncMock(return_value=([], 0))),
    ):
        result = await service.send_all_digests()

    assert result.subscriptions_processed == 1
    assert result.emails_sent == 0


async def test_send_all_digests_skips_already_sent_jobs():
    session = _mock_session()
    service = SubscriptionService(session=session)
    sub = _make_sub()
    job = _make_job()

    with (
        patch.object(service._sub_repo, "get_all_active", new=AsyncMock(return_value=[sub])),
        patch.object(service._job_repo, "list_jobs", new=AsyncMock(return_value=([job], 1))),
        patch.object(service._send_repo, "get_sent_job_ids", new=AsyncMock(return_value={job.id})),
    ):
        result = await service.send_all_digests()

    assert result.emails_sent == 0


async def test_send_all_digests_sends_email_for_new_jobs():
    session = _mock_session()
    service = SubscriptionService(session=session)
    sub = _make_sub()
    job = _make_job()

    with (
        patch.object(service._sub_repo, "get_all_active", new=AsyncMock(return_value=[sub])),
        patch.object(service._job_repo, "list_jobs", new=AsyncMock(return_value=([job], 1))),
        patch.object(service._send_repo, "get_sent_job_ids", new=AsyncMock(return_value=set())),
        patch.object(service._send_repo, "record_sends", new=AsyncMock()),
        patch("app.services.subscription_service._send_email") as mock_send,
    ):
        result = await service.send_all_digests()

    assert result.emails_sent == 1
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args
    assert call_kwargs.kwargs["to"] == "test@example.com"


async def test_send_all_digests_records_sends_after_email():
    session = _mock_session()
    service = SubscriptionService(session=session)
    sub = _make_sub()
    job = _make_job()

    with (
        patch.object(service._sub_repo, "get_all_active", new=AsyncMock(return_value=[sub])),
        patch.object(service._job_repo, "list_jobs", new=AsyncMock(return_value=([job], 1))),
        patch.object(service._send_repo, "get_sent_job_ids", new=AsyncMock(return_value=set())),
        patch.object(service._send_repo, "record_sends", new=AsyncMock()) as mock_record,
        patch("app.services.subscription_service._send_email"),
    ):
        await service.send_all_digests()

    mock_record.assert_called_once()
    _, recorded_job_ids, _ = mock_record.call_args.args
    assert job.id in recorded_job_ids


async def test_send_all_digests_no_active_subscriptions():
    session = _mock_session()
    service = SubscriptionService(session=session)

    with patch.object(service._sub_repo, "get_all_active", new=AsyncMock(return_value=[])):
        result = await service.send_all_digests()

    assert result == DigestResult(subscriptions_processed=0, emails_sent=0)
