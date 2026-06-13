"""
Redis Health Checker

Monitors Redis connectivity and performance.
"""

import time
from typing import Optional

from app.core.interfaces.health_check_interface import IHealthChecker
from app.core.health_check_types import ComponentHealth, HealthStatus
from app.core.redis_client import get_redis


class RedisHealthChecker(IHealthChecker):
    """
    Health checker for Redis.

    Checks:
    - Redis connectivity
    - Basic operations (PING)
    - Memory usage
    - Connection count
    - Response time
    """

    def __init__(self, timeout: float = 3.0):
        """
        Initialize Redis health checker.

        Args:
            timeout: Operation timeout in seconds
        """
        self.timeout = timeout

    async def check_health(self) -> ComponentHealth:
        """
        Perform Redis health check.

        Returns:
            ComponentHealth: Redis health status with details
        """
        start_time = time.time()
        metadata = {}

        try:
            redis_client = get_redis()

            # Test basic connectivity with PING
            ping_start = time.time()
            pong = redis_client.ping()
            ping_time = (time.time() - ping_start) * 1000

            if not pong:
                return ComponentHealth(
                    component_name=self.get_check_type(),
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=round((time.time() - start_time) * 1000, 2),
                    details="Redis PING failed",
                    metadata=metadata,
                    is_critical=self.is_critical(),
                )

            # Get Redis info
            info = redis_client.info()

            # Extract key metrics
            metadata = {
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "used_memory_peak_human": info.get("used_memory_peak_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "uptime_days": info.get("uptime_in_days", 0),
                "ping_time_ms": round(ping_time, 2),
            }

            response_time = (time.time() - start_time) * 1000

            # Determine health based on response time
            if response_time > 1000:  # More than 1 second is degraded
                return ComponentHealth(
                    component_name=self.get_check_type(),
                    status=HealthStatus.DEGRADED,
                    response_time_ms=round(response_time, 2),
                    details=f"Redis response slow: {response_time:.2f}ms",
                    metadata=metadata,
                    is_critical=self.is_critical(),
                )

            return ComponentHealth(
                component_name=self.get_check_type(),
                status=HealthStatus.HEALTHY,
                response_time_ms=round(response_time, 2),
                details="Redis connection successful",
                metadata=metadata,
                is_critical=self.is_critical(),
            )

        except Exception as e:
            return ComponentHealth(
                component_name=self.get_check_type(),
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round((time.time() - start_time) * 1000, 2),
                details=f"Redis connection failed: {str(e)}",
                metadata=metadata,
                is_critical=self.is_critical(),
            )

    def get_check_type(self) -> str:
        """Get checker type identifier."""
        return "redis"

    def is_critical(self) -> bool:
        """Redis is critical for system operation (caching, sessions)."""
        return True

    def get_timeout_seconds(self) -> float:
        """Get timeout for Redis health check."""
        return self.timeout
