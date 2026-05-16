from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source


class SourceRepository:
    """Read-only access to the sources table. Sources are seed data, not user-created."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> Source | None:
        """Fetch a source by its unique name (e.g. 'remoteok').

        Args:
            name: The source's unique name.

        Returns:
            The Source ORM model, or None if not found.
        """
        result = await self._session.execute(
            select(Source).where(Source.name == name)
        )
        return result.scalar_one_or_none()
