"""
Redis cache management
"""

from typing import Optional, Any
import json

import structlog
import redis.asyncio as redis

from app.core.config import settings

logger = structlog.get_logger()

# Redis client
redis_client: Optional[redis.Redis] = None


async def init_cache() -> None:
    """Initialize Redis connection."""
    global redis_client
    logger.info("Initializing Redis connection", url=settings.REDIS_URL)
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    # Test connection
    await redis_client.ping()
    logger.info("Redis connection established")


async def close_cache() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        logger.info("Closing Redis connection")
        await redis_client.close()


async def get_cache(key: str) -> Optional[Any]:
    """Get value from cache."""
    if not redis_client:
        return None

    value = await redis_client.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


async def set_cache(
    key: str,
    value: Any,
    ttl_seconds: int = None
) -> bool:
    """Set value in cache."""
    if not redis_client:
        return False

    ttl = ttl_seconds or settings.CACHE_TTL_SECONDS

    if isinstance(value, (dict, list)):
        value = json.dumps(value)

    await redis_client.setex(key, ttl, value)
    return True


async def delete_cache(key: str) -> bool:
    """Delete value from cache."""
    if not redis_client:
        return False

    await redis_client.delete(key)
    return True


async def clear_pattern(pattern: str) -> int:
    """Delete all keys matching pattern."""
    if not redis_client:
        return 0

    count = 0
    async for key in redis_client.scan_iter(match=pattern):
        await redis_client.delete(key)
        count += 1

    return count


def cache_key(*parts: str) -> str:
    """Generate cache key from parts."""
    return ":".join(["viral_weather"] + list(parts))
