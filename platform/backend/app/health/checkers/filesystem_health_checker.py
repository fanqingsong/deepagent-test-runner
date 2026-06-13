"""
File System Health Checker

Monitors file system health and disk space.
"""

import time
import os
import shutil
from typing import Optional

from app.core.interfaces.health_check_interface import IHealthChecker
from app.core.health_check_types import ComponentHealth, HealthStatus
from app.core.config import settings


class FileSystemHealthChecker(IHealthChecker):
    """
    Health checker for file system.

    Checks:
    - Disk space availability
    - File system access
    - Directory permissions
    - Important directories exist
    """

    def __init__(self, timeout: float = 2.0, warning_threshold_percent: float = 80.0):
        """
        Initialize file system health checker.

        Args:
            timeout: Operation timeout in seconds
            warning_threshold_percent: Disk usage warning threshold (default: 80%)
        """
        self.timeout = timeout
        self.warning_threshold_percent = warning_threshold_percent

    async def check_health(self) -> ComponentHealth:
        """
        Perform file system health check.

        Returns:
            ComponentHealth: File system health status with details
        """
        start_time = time.time()
        metadata = {}

        try:
            # Get disk usage for current directory
            stat = os.statvfs("/")
            if stat:
                total_space = stat.f_blocks * stat.f_frsize
                free_space = stat.f_bavail * stat.f_frsize
                used_space = total_space - free_space
                usage_percent = (used_space / total_space) * 100 if total_space > 0 else 0

                metadata = {
                    "total_space_gb": round(total_space / (1024**3), 2),
                    "free_space_gb": round(free_space / (1024**3), 2),
                    "used_space_gb": round(used_space / (1024**3), 2),
                    "usage_percent": round(usage_percent, 2),
                    "check_path": "/",
                }

                # Check important directories
                important_dirs = [settings.SCREENSHOT_DIR]
                accessible_dirs = []
                inaccessible_dirs = []

                for dir_path in important_dirs:
                    try:
                        # Create directory if it doesn't exist
                        os.makedirs(dir_path, exist_ok=True)

                        # Test write access
                        test_file = os.path.join(dir_path, ".health_check_test")
                        with open(test_file, 'w') as f:
                            f.write('test')
                        os.remove(test_file)

                        accessible_dirs.append(dir_path)
                    except Exception:
                        inaccessible_dirs.append(dir_path)

                metadata["accessible_important_dirs"] = accessible_dirs
                metadata["inaccessible_important_dirs"] = inaccessible_dirs

                # Determine health status
                status = HealthStatus.HEALTHY
                details = "File system healthy"

                # Check disk usage
                if usage_percent >= 95:
                    status = HealthStatus.UNHEALTHY
                    details = f"Disk critically full: {usage_percent:.1f}% used"
                elif usage_percent >= self.warning_threshold_percent:
                    status = HealthStatus.DEGRADED
                    details = f"Disk space warning: {usage_percent:.1f}% used"

                # Check directory access
                if inaccessible_dirs:
                    status = HealthStatus.DEGRADED if status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
                    details += f", {len(inaccessible_dirs)} dirs inaccessible"

                response_time = (time.time() - start_time) * 1000

                return ComponentHealth(
                    component_name=self.get_check_type(),
                    status=status,
                    response_time_ms=round(response_time, 2),
                    details=details,
                    metadata=metadata,
                    is_critical=self.is_critical(),
                )
            else:
                return ComponentHealth(
                    component_name=self.get_check_type(),
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=round((time.time() - start_time) * 1000, 2),
                    details="Unable to get file system stats",
                    metadata=metadata,
                    is_critical=self.is_critical(),
                )

        except Exception as e:
            return ComponentHealth(
                component_name=self.get_check_type(),
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round((time.time() - start_time) * 1000, 2),
                details=f"File system check failed: {str(e)}",
                metadata=metadata,
                is_critical=self.is_critical(),
            )

    def get_check_type(self) -> str:
        """Get checker type identifier."""
        return "filesystem"

    def is_critical(self) -> bool:
        """File system is critical (cannot operate without disk space)."""
        return True

    def get_timeout_seconds(self) -> float:
        """Get timeout for file system health check."""
        return self.timeout
