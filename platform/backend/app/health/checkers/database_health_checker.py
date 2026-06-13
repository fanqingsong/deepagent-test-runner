"""
Database Health Checker

Monitors PostgreSQL database connectivity and performance.
"""

import time
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.interfaces.health_check_interface import IHealthChecker
from app.core.health_check_types import ComponentHealth, HealthStatus
from app.core.database import async_session_maker


class DatabaseHealthChecker(IHealthChecker):
    """
    Health checker for PostgreSQL database.

    Checks:
    - Database connectivity
    - Basic query execution
    - Connection pool health
    - Response time monitoring
    """

    def __init__(self, timeout: float = 5.0):
        """
        Initialize database health checker.

        Args:
            timeout: Query timeout in seconds
        """
        self.timeout = timeout

    async def check_health(self) -> ComponentHealth:
        """
        Perform database health check.

        Returns:
            ComponentHealth: Database health status with details
        """
        start_time = time.time()
        metadata = {}

        try:
            async with async_session_maker() as session:
                # Test basic connectivity with simple query
                result = await session.execute(text("SELECT 1 as test_value"))
                row = result.fetchone()

                if row and row[0] == 1:
                    # Test query performance
                    perf_start = time.time()
                    await session.execute(text("SELECT COUNT(*) FROM information_schema.tables"))
                    perf_time = (time.time() - perf_start) * 1000

                    # Get database size
                    size_result = await session.execute(text("""
                        SELECT pg_size_pretty(pg_database_size(current_database()))
                    """))
                    db_size = size_result.scalar()

                    # Get connection pool info
                    pool_result = await session.execute(text("""
                        SELECT count(*) FROM pg_stat_activity
                        WHERE datname = current_database()
                    """))
                    active_connections = pool_result.scalar()

                    metadata = {
                        "database_size": db_size,
                        "active_connections": active_connections,
                        "query_performance_ms": round(perf_time, 2),
                        "test_query": "SELECT 1 passed"
                    }

                    response_time = (time.time() - start_time) * 1000

                    # Determine health based on response time
                    if response_time > 2000:  # More than 2 seconds is degraded
                        return ComponentHealth(
                            component_name=self.get_check_type(),
                            status=HealthStatus.DEGRADED,
                            response_time_ms=round(response_time, 2),
                            details=f"Database response slow: {response_time:.2f}ms",
                            metadata=metadata,
                            is_critical=self.is_critical(),
                        )

                    return ComponentHealth(
                        component_name=self.get_check_type(),
                        status=HealthStatus.HEALTHY,
                        response_time_ms=round(response_time, 2),
                        details="Database connection successful",
                        metadata=metadata,
                        is_critical=self.is_critical(),
                    )
                else:
                    return ComponentHealth(
                        component_name=self.get_check_type(),
                        status=HealthStatus.UNHEALTHY,
                        response_time_ms=round((time.time() - start_time) * 1000, 2),
                        details="Database query returned unexpected result",
                        metadata=metadata,
                        is_critical=self.is_critical(),
                    )

        except Exception as e:
            return ComponentHealth(
                component_name=self.get_check_type(),
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round((time.time() - start_time) * 1000, 2),
                details=f"Database connection failed: {str(e)}",
                metadata=metadata,
                is_critical=self.is_critical(),
            )

    def get_check_type(self) -> str:
        """Get checker type identifier."""
        return "database"

    def is_critical(self) -> bool:
        """Database is critical for system operation."""
        return True

    def get_timeout_seconds(self) -> float:
        """Get timeout for database health check."""
        return self.timeout
