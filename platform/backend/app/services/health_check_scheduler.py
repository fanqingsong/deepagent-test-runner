"""
Health Check Scheduler

Background task to run periodic health checks and store results for trending.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

from app.services.health_check_service import health_check_service
from app.core.health_check_types import HealthStatus

logger = logging.getLogger(__name__)


class HealthCheckScheduler:
    """
    Scheduler for periodic health checks.

    Features:
    - Configurable check interval
    - Background task execution
    - Health status trending
    - Alert on degraded/unhealthy status
    """

    def __init__(
        self,
        check_interval_seconds: int = 300,  # 5 minutes default
        alert_on_degraded: bool = True,
        alert_on_unhealthy: bool = True,
    ):
        """
        Initialize health check scheduler.

        Args:
            check_interval_seconds: Interval between health checks (default: 300)
            alert_on_degraded: Whether to log alerts on degraded status
            alert_on_unhealthy: Whether to log alerts on unhealthy status
        """
        self.check_interval_seconds = check_interval_seconds
        self.alert_on_degraded = alert_on_degraded
        self.alert_on_unhealthy = alert_on_unhealthy

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_status: Optional[HealthStatus] = None

    async def start(self) -> None:
        """Start the health check scheduler."""
        if self._running:
            logger.warning("Health check scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_health_checks())
        logger.info(
            f"Health check scheduler started (interval: {self.check_interval_seconds}s)"
        )

    async def stop(self) -> None:
        """Stop the health check scheduler."""
        if not self._running:
            logger.warning("Health check scheduler is not running")
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Health check scheduler stopped")

    async def _run_health_checks(self) -> None:
        """Run periodic health checks."""
        while self._running:
            try:
                # Perform health check
                result = await health_check_service.check_health()

                # Log status changes
                self._log_status_change(result.status)

                # Alert on unhealthy/degraded status
                if result.status == HealthStatus.UNHEALTHY and self.alert_on_unhealthy:
                    logger.error(
                        f"System health check: UNHEALTHY - {result.details}"
                    )

                elif result.status == HealthStatus.DEGRADED and self.alert_on_degraded:
                    logger.warning(
                        f"System health check: DEGRADED - {result.details}"
                    )

                elif result.status == HealthStatus.HEALTHY:
                    logger.info("System health check: HEALTHY")

                # Update last status
                self._last_status = result.status

            except Exception as e:
                logger.error(f"Health check failed: {e}")

            # Wait for next check
            await asyncio.sleep(self.check_interval_seconds)

    def _log_status_change(self, current_status: HealthStatus) -> None:
        """Log if health status has changed."""
        if self._last_status and self._last_status != current_status:
            logger.warning(
                f"System health status changed: {self._last_status.value} -> {current_status.value}"
            )

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    def get_last_status(self) -> Optional[HealthStatus]:
        """Get the last known health status."""
        return self._last_status


# Global scheduler instance
health_check_scheduler = HealthCheckScheduler()


async def start_health_check_scheduler() -> None:
    """Start the global health check scheduler."""
    await health_check_scheduler.start()


async def stop_health_check_scheduler() -> None:
    """Stop the global health check scheduler."""
    await health_check_scheduler.stop()
