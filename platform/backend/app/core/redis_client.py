"""
Redis Client Module

Provides centralized Redis client management for the application.
"""

import redis
from app.core.config import settings


def get_redis() -> redis.Redis:
    """
    Get Redis client instance.

    Returns:
        redis.Redis: Redis client with decode_responses enabled

    Example:
        >>> from app.core.redis_client import get_redis
        >>> client = get_redis()
        >>> client.set("key", "value")
        >>> client.get("key")
    """
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
