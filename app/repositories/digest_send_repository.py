import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digest_send import DigestSend


class DigestSendRepository:
    """Tracks which jobs have been emailed to which subscribers (idempotency log)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_sent_job_ids(self, subscription_id: uuid.UUID) -> set[uuid.UUID]:
        """Return UUIDs of all jobs already sent to this subscriber.

        Single query — used to filter out already-sent jobs before building digest.

        Args:
            subscription_id: UUID of the subscription.

        Returns:
            Set of job UUIDs already emailed to this subscriber.
        """
        result = await self._session.execute(
            select(DigestSend.job_id).where(
                DigestSend.subscription_id == subscription_id
            )
        )
        return set(result.scalars().all())

    async def record_sends(
        self,
        subscription_id: uuid.UUID,
        job_ids: list[uuid.UUID],
        sent_at: datetime,
    ) -> None:
        """Insert DigestSend rows for a batch of jobs sent to one subscriber.

        The unique constraint (subscription_id, job_id) prevents duplicates
        if this is called twice for the same batch (e.g. task retry).

        Args:
            subscription_id: UUID of the subscription.
            job_ids: UUIDs of jobs included in this digest email.
            sent_at: Timestamp of when the email was sent.
        """
        for job_id in job_ids:
            send = DigestSend(
                subscription_id=subscription_id,
                job_id=job_id,
                sent_at=sent_at,
            )
            self._session.add(send)
        await self._session.flush()
