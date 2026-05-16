import structlog

from app.repositories.dedup_key_repository import DedupKeyRepository
from app.schemas.normalized_job import NormalizedJob

log = structlog.get_logger()


async def deduplicate_items(
    items: list[NormalizedJob],
    dedup_repo: DedupKeyRepository,
) -> list[NormalizedJob]:
    """Filter out items whose dedup_hash already exists in dedup_keys.

    Uses a single bulk query — one DB round-trip for the entire batch,
    not one per item.

    Args:
        items: Normalized items from the normalize stage.
        dedup_repo: Repository for dedup_keys table access.

    Returns:
        Subset of items that are new (not already in the DB).
    """
    if not items:
        return []

    hashes = [item.dedup_hash for item in items]
    existing_hashes = await dedup_repo.bulk_exists(hashes)

    new_items = [item for item in items if item.dedup_hash not in existing_hashes]

    log.info(
        "dedup_complete",
        total=len(items),
        duplicates=len(existing_hashes),
        new=len(new_items),
    )
    return new_items
