from collections.abc import AsyncGenerator
import redis.asyncio as aioredis
from app.config import settings

# Create Redis connection pool with max connections limit and decoded responses
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)

def get_redis_client() -> aioredis.Redis:
    """Return an async Redis client using the shared connection pool."""
    return aioredis.Redis(connection_pool=redis_pool)

async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Dependency injection yield for Redis connection."""
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()
