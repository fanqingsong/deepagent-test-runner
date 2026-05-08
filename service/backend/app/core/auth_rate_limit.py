import redis
import time
from typing import Tuple
from app.core.config import settings

# Redis client for rate limiting
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def check_rate_limit(
    identifier: str,
    max_attempts: int,
    window_seconds: int,
    prefix: str = "ratelimit"
) -> Tuple[bool, int, int]:
    """
    Sliding window rate limiting using Redis sorted sets.

    Args:
        identifier: Unique identifier (IP address, user_id, etc.)
        max_attempts: Maximum number of attempts allowed
        window_seconds: Time window in seconds
        prefix: Redis key prefix

    Returns:
        Tuple of (is_allowed, remaining_attempts, retry_after_seconds)
    """
    key = f"{prefix}:{identifier}"
    current_time = time.time()

    # Remove entries outside the time window
    redis_client.zremrangebyscore(key, 0, current_time - window_seconds)

    # Count attempts in the window
    attempts = redis_client.zcard(key)

    if attempts >= max_attempts:
        # Rate limit exceeded - calculate retry after time
        oldest_attempt = float(redis_client.zrange(key, 0, 0, withscores=True)[0][1])
        retry_after = int(oldest_attempt + window_seconds - current_time) + 1
        return False, 0, retry_after

    # Add current attempt
    pipe = redis_client.pipeline()
    pipe.zadd(key, {str(current_time): current_time})
    pipe.expire(key, window_seconds)
    pipe.execute()

    remaining = max_attempts - attempts - 1
    return True, remaining, 0


async def reset_rate_limit(identifier: str, prefix: str = "ratelimit"):
    """Reset rate limit for a specific identifier"""
    key = f"{prefix}:{identifier}"
    redis_client.delete(key)
