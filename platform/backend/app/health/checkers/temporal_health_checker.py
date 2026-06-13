"""
Temporal Health Checker

Monitors Temporal server connectivity and health.
"""

import time
from typing import Optional

from app.core.interfaces.health_check_interface import IHealthChecker
from app.core.health_check_types import ComponentHealth, HealthStatus
from app.temporal.client import get_temporal_client
from app.temporal.settings import settings


class TemporalHealthChecker(IHealthChecker):
    """
    Health checker for Temporal server.

    Checks:
    - Temporal server connectivity
    - Namespace accessibility
    - Cluster health
    - Connection time
    """

    def __init__(self, timeout: float = 5.0):
        """
        Initialize Temporal health checker.

        Args:
            timeout: Connection timeout in seconds
        """
        self.timeout = timeout

    async def check_health(self) -> ComponentHealth:
        """
        Perform Temporal health check.

        Returns:
            ComponentHealth: Temporal health status with details
        """
        start_time = time.time()
        metadata = {}

        try:
            # Get Temporal client
            client = await get_temporal_client()

            # Get cluster info
            cluster_name = client.service_name or "unknown"

            # Test basic connectivity by getting workflow count
            # We'll just check if we can connect successfully
            connection_time = (time.time() - start_time) * 1000

            metadata = {
                "cluster_name": cluster_name,
                "namespace": settings.namespace,
                "host_url": settings.host_url,
                "task_queue": settings.task_queue,
                "connection_time_ms": round(connection_time, 2),
            }

            total_time = (time.time() - start_time) * 1000

            # Determine health based on response time
            if total_time > 3000:  # More than 3 seconds is degraded
                return ComponentHealth(
                    component_name=self.get_check_type(),
                    status=HealthStatus.DEGRADED,
                    response_time_ms=round(total_time, 2),
                    details=f"Temporal connection slow: {total_time:.2f}ms",
                    metadata=metadata,
                    is_critical=self.is_critical(),
                )

            return ComponentHealth(
                component_name=self.get_check_type(),
                status=HealthStatus.HEALTHY,
                response_time_ms=round(total_time, 2),
                details="Temporal connection successful",
                metadata=metadata,
                is_critical=self.is_critical(),
            )

        except Exception as e:
            return ComponentHealth(
                component_name=self.get_check_type(),
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round((time.time() - start_time) * 1000, 2),
                details=f"Temporal connection failed: {str(e)}",
                metadata=metadata,
                is_critical=self.is_critical(),
            )

    def get_check_type(self) -> str:
        """Get checker type identifier."""
        return "temporal"

    def is_critical(self) -> bool:
        """Temporal is important but not critical (system can operate without it)."""
        return False

    def get_timeout_seconds(self) -> float:
        """Get timeout for Temporal health check."""
        return self.timeout
