"""
Health Check Interface

Defines the interface for health checkers following SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.core.health_check_types import HealthCheckResult, ComponentHealth, HealthStatus


class IHealthChecker(ABC):
    """
    Interface for health check implementations.

    All health checkers must implement this interface to ensure
    consistent health checking across the system.
    """

    @abstractmethod
    async def check_health(self) -> ComponentHealth:
        """
        Perform health check for this component.

        Returns:
            ComponentHealth: Health check result with status and details

        Raises:
            Exception: If health check fails (will be caught and converted to UNHEALTHY status)
        """
        pass

    @abstractmethod
    def get_check_type(self) -> str:
        """
        Get the type/identifier of this health checker.

        Returns:
            str: Unique identifier for this checker (e.g., 'database', 'redis', 'llm')
        """
        pass

    @abstractmethod
    def is_critical(self) -> bool:
        """
        Determine if this component is critical for system operation.

        Returns:
            bool: True if system cannot operate without this component
        """
        pass

    def get_timeout_seconds(self) -> float:
        """
        Get timeout for this health check.

        Returns:
            float: Timeout in seconds (default: 5.0)
        """
        return 5.0

    def should_run(self, config: Optional[dict] = None) -> bool:
        """
        Determine if this health check should run based on configuration.

        Args:
            config: Optional configuration dictionary

        Returns:
            bool: True if this check should run
        """
        if config and config.get("critical_only") and not self.is_critical():
            return False
        return True

    async def safe_check(self) -> ComponentHealth:
        """
        Safely perform health check with error handling.

        This wrapper ensures that health check failures don't crash
        the health check system. Errors are converted to UNHEALTHY status.

        Returns:
            ComponentHealth: Health check result with status and details
        """
        import time
        start_time = time.time()

        try:
            result = await self.check_health()
            # Ensure response time is set
            if result.response_time_ms is None:
                result.response_time_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            # Convert exceptions to UNHEALTHY status
            return ComponentHealth(
                component_name=self.get_check_type(),
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details=f"Health check failed: {str(e)}",
                is_critical=self.is_critical(),
            )


__all__ = ["IHealthChecker"]
