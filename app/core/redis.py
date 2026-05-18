from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    """Return (or lazily create) the shared Redis connection pool.

    Returns:
        Shared aioredis ConnectionPool instance.
    """
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(settings.redis_url)
    return _pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency that yields an async Redis client.

    Yields:
        An aioredis.Redis client backed by the shared pool.
    """
    client: aioredis.Redis = aioredis.Redis(connection_pool=get_redis_pool())
    try:
        yield client
    finally:
        await client.aclose()
