from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.pipelines.deduplicate import deduplicate_items
from app.repositories.dedup_key_repository import DedupKeyRepository
from app.schemas.normalized_job import NormalizedJob

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_normalized(
    dedup_hash: str, source_url: str = "https://example.com/job/1"
) -> NormalizedJob:
    return NormalizedJob(
        title="Dev",
        company="Acme",
        description="desc",
        tags=["python"],
        salary_min=None,
        salary_max=None,
        currency="USD",
        posted_at=_NOW,
        source_url=source_url,
        source_name="remoteok",
        dedup_hash=dedup_hash,
    )


def _mock_dedup_repo(existing_keys: set[str]) -> DedupKeyRepository:
    repo = MagicMock(spec=DedupKeyRepository)
    repo.bulk_exists = AsyncMock(return_value=existing_keys)
    return repo


async def test_deduplicate_returns_all_when_none_exist():
    items = [_make_normalized("aaa"), _make_normalized("bbb", "https://example.com/2")]
    repo = _mock_dedup_repo(existing_keys=set())

    result = await deduplicate_items(items, repo)

    assert len(result) == 2


async def test_deduplicate_filters_existing_hashes():
    items = [
        _make_normalized("aaa"),
        _make_normalized("bbb", "https://example.com/2"),
    ]
    repo = _mock_dedup_repo(existing_keys={"aaa"})

    result = await deduplicate_items(items, repo)

    assert len(result) == 1
    assert result[0].dedup_hash == "bbb"


async def test_deduplicate_returns_empty_when_all_exist():
    items = [_make_normalized("aaa"), _make_normalized("bbb", "https://example.com/2")]
    repo = _mock_dedup_repo(existing_keys={"aaa", "bbb"})

    result = await deduplicate_items(items, repo)

    assert result == []


async def test_deduplicate_empty_input_skips_db_query():
    repo = _mock_dedup_repo(existing_keys=set())

    result = await deduplicate_items([], repo)

    assert result == []
    repo.bulk_exists.assert_not_called()


async def test_deduplicate_passes_all_hashes_to_repo():
    items = [
        _make_normalized("hash1"),
        _make_normalized("hash2", "https://example.com/2"),
    ]
    repo = _mock_dedup_repo(existing_keys=set())

    await deduplicate_items(items, repo)

    called_keys = repo.bulk_exists.call_args[0][0]
    assert set(called_keys) == {"hash1", "hash2"}
