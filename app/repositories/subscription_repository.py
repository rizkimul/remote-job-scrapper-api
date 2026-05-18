from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digest_subscription import DigestSubscription


class SubscriptionRepository:
    """CRUD for digest_subscriptions table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> DigestSubscription | None:
        """Fetch a subscription by email address.

        Args:
            email: Normalised (lowercase) email address.

        Returns:
            DigestSubscription or None.
        """
        result = await self._session.execute(
            select(DigestSubscription).where(DigestSubscription.email == email)
        )
        return result.scalar_one_or_none()

    async def create_or_reactivate(
        self,
        email: str,
        tags_filter: list[str] | None,
        min_salary: int | None,
    ) -> DigestSubscription:
        """Insert a new subscription or reactivate an existing one.

        If the email already exists (even if inactive), update its filters
        and set is_active=True. This makes subscribing idempotent.

        Args:
            email: Normalised email address.
            tags_filter: Optional tag filter list.
            min_salary: Optional minimum salary.

        Returns:
            Persisted DigestSubscription.
        """
        existing = await self.get_by_email(email)
        if existing:
            existing.tags_filter = tags_filter
            existing.min_salary = min_salary
            existing.is_active = True
            existing.confirmed_at = datetime.now(tz=UTC)
            await self._session.flush()
            return existing

        sub = DigestSubscription(
            email=email,
            tags_filter=tags_filter,
            min_salary=min_salary,
            is_active=True,
            confirmed_at=datetime.now(tz=UTC),
        )
        self._session.add(sub)
        await self._session.flush()
        return sub

    async def deactivate(self, email: str) -> bool:
        """Soft-delete a subscription by setting is_active=False.

        Args:
            email: Normalised email address.

        Returns:
            True if found and deactivated, False if not found.
        """
        sub = await self.get_by_email(email)
        if sub is None:
            return False
        sub.is_active = False
        await self._session.flush()
        return True

    async def get_all_active(self) -> list[DigestSubscription]:
        """Return all active subscriptions. Used by the send_digest task."""
        result = await self._session.execute(
            select(DigestSubscription).where(DigestSubscription.is_active.is_(True))
        )
        return list(result.scalars().all())
