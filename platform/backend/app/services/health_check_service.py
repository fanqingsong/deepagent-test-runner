"""
Health Check Service

Orchestrates health checks for all system components and aggregates results.
"""

import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from app.core.interfaces.health_check_interface import IHealthChecker
from app.core.health_check_types import (
    HealthCheckResult,
    SystemHealth,
    HealthCheckConfig,
    HealthHistory,
    HealthStatus,
    ComponentHealth,
)
from app.health.checkers import (
    DatabaseHealthChecker,
    RedisHealthChecker,
    LLMHealthChecker,
    TemporalHealthChecker,
    FileSystemHealthChecker,
)


class HealthCheckService:
    """
    Service for performing health checks on all system components.

    Features:
    - Parallel execution of health checks
    - Result aggregation and status calculation
    - Caching with TTL
    - Critical-only checks option
    - Historical health tracking
    """

    def __init__(self):
        """Initialize health check service with all checkers."""
        self.checkers: List[IHealthChecker] = [
            DatabaseHealthChecker(),
            RedisHealthChecker(),
            LLMHealthChecker(),
            TemporalHealthChecker(),
            FileSystemHealthChecker(),
        ]

        # Cache for health check results
        self._cache: Optional[HealthCheckResult] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl: timedelta = timedelta(seconds=60)

        # Historical data
        self._history: List[HealthHistory] = []
        self._max_history_size = 100

    def get_checker(self, checker_type: str) -> Optional[IHealthChecker]:
        """
        Get a specific health checker by type.

        Args:
            checker_type: Type identifier (e.g., 'database', 'redis')

        Returns:
            IHealthChecker or None: The requested checker if found
        """
        for checker in self.checkers:
            if checker.get_check_type() == checker_type:
                return checker
        return None

    async def check_health(
        self,
        config: Optional[HealthCheckConfig] = None
    ) -> HealthCheckResult:
        """
        Perform health check on all components.

        Args:
            config: Optional health check configuration

        Returns:
            HealthCheckResult: Aggregated health check results
        """
        start_time = time.time()
        config = config or HealthCheckConfig()

        # Check cache first
        if self._is_cache_valid(config):
            return self._cache

        # Create system health object
        system_health = SystemHealth(
            status=HealthStatus.UNKNOWN,
            timestamp=datetime.utcnow(),
            components={},
        )

        # Filter checkers based on configuration
        active_checkers = self._filter_checkers(config)

        # Execute health checks
        if config.parallel_execution:
            # Parallel execution
            tasks = [
                checker.safe_check()
                for checker in active_checkers
                if checker.should_run({"critical_only": config.critical_only})
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Sequential execution
            results = []
            for checker in active_checkers:
                if checker.should_run({"critical_only": config.critical_only}):
                    try:
                        result = await checker.safe_check()
                        results.append(result)
                    except Exception as e:
                        # This shouldn't happen due to safe_check, but handle it
                        results.append(
                            ComponentHealth(
                                component_name=checker.get_check_type(),
                                status=HealthStatus.UNHEALTHY,
                                details=f"Check failed: {str(e)}",
                                is_critical=checker.is_critical(),
                            )
                        )

        # Add results to system health
        for result in results:
            if isinstance(result, ComponentHealth):
                system_health.add_component(result)

        # Calculate overall status
        system_health.calculate_overall_status()
        system_health.response_time_ms = round((time.time() - start_time) * 1000, 2)

        # Update cache
        self._update_cache(system_health, config)

        # Add to history
        self._add_to_history(system_health)

        return system_health

    async def check_component(self, component_type: str) -> ComponentHealth:
        """
        Perform health check on a specific component.

        Args:
            component_type: Type of component to check

        Returns:
            ComponentHealth: Health check result for the component

        Raises:
            ValueError: If component type not found
        """
        checker = self.get_checker(component_type)
        if not checker:
            raise ValueError(f"Unknown component type: {component_type}")

        return await checker.safe_check()

    async def check_critical_only(self) -> HealthCheckResult:
        """
        Perform health check on critical components only.

        Returns:
            HealthCheckResult: Aggregated health check results
        """
        config = HealthCheckConfig(
            critical_only=True,
            parallel_execution=True,
        )
        return await self.check_health(config)

    def get_history(self, limit: int = 10) -> List[HealthHistory]:
        """
        Get health check history.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List[HealthHistory]: Historical health check results
        """
        return self._history[-limit:]

    def get_status_summary(self) -> Dict[str, any]:
        """
        Get a summary of current health status.

        Returns:
            Dict with status summary
        """
        if not self._cache:
            return {
                "status": "unknown",
                "message": "No health check data available",
            }

        return {
            "status": self._cache.status.value,
            "total_components": self._cache.total_components,
            "healthy_components": self._cache.healthy_components,
            "degraded_components": self._cache.degraded_components,
            "unhealthy_components": self._cache.unhealthy_components,
            "last_check": self._cache.timestamp.isoformat(),
            "details": self._cache.details,
        }

    def clear_cache(self) -> None:
        """Clear health check cache."""
        self._cache = None
        self._cache_time = None

    def _filter_checkers(self, config: HealthCheckConfig) -> List[IHealthChecker]:
        """
        Filter checkers based on configuration.

        Args:
            config: Health check configuration

        Returns:
            List[IHealthChecker]: Filtered list of checkers
        """
        if config.critical_only:
            return [c for c in self.checkers if c.is_critical()]

        if config.include_non_critical:
            return self.checkers

        return [c for c in self.checkers if c.is_critical()]

    def _is_cache_valid(self, config: HealthCheckConfig) -> bool:
        """
        Check if cache is valid.

        Args:
            config: Health check configuration

        Returns:
            bool: True if cache is valid
        """
        if not self._cache or not self._cache_time:
            return False

        # Check cache age
        cache_age = datetime.utcnow() - self._cache_time
        if cache_age > timedelta(seconds=config.cache_ttl_seconds):
            return False

        return True

    def _update_cache(
        self,
        result: HealthCheckResult,
        config: HealthCheckConfig
    ) -> None:
        """
        Update health check cache.

        Args:
            result: Health check result to cache
            config: Health check configuration
        """
        self._cache = result
        self._cache_time = datetime.utcnow()
        self._cache_ttl = timedelta(seconds=config.cache_ttl_seconds)

    def _add_to_history(self, result: HealthCheckResult) -> None:
        """
        Add health check result to history.

        Args:
            result: Health check result to add
        """
        history_entry = HealthHistory(
            timestamp=result.timestamp,
            status=result.status,
            response_time_ms=result.response_time_ms or 0,
            component_count=result.total_components,
            unhealthy_count=result.unhealthy_components,
        )

        self._history.append(history_entry)

        # Keep history size limited
        if len(self._history) > self._max_history_size:
            self._history = self._history[-self._max_history_size:]


# Singleton instance
health_check_service = HealthCheckService()
