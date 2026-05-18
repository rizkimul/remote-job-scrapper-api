import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dedup_key import DedupKey


class DedupKeyRepository:
    """Manages dedup_keys table. Used by the deduplicate pipeline stage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_exists(self, keys: list[str]) -> set[str]:
        """Return the subset of keys that already exist in dedup_keys.

        Single query using ANY(:keys) instead of N individual lookups.

        Args:
            keys: List of SHA-256 hex digests to check.

        Returns:
            Set of keys that are already stored (i.e. duplicate jobs).
        """
        if not keys:
            return set()
        result = await self._session.execute(
            select(DedupKey.key).where(DedupKey.key.in_(keys))
        )
        return set(result.scalars().all())

    async def create(
        self,
        key: str,
        job_id: uuid.UUID,
        source_id: uuid.UUID,
    ) -> DedupKey:
        """Insert a new DedupKey record.

        Args:
            key: SHA-256 hex digest.
            job_id: UUID of the associated Job.
            source_id: UUID of the source that produced this job.

        Returns:
            Persisted DedupKey instance.
        """
        dedup = DedupKey(key=key, job_id=job_id, source_id=source_id)
        self._session.add(dedup)
        await self._session.flush()
        return dedup
