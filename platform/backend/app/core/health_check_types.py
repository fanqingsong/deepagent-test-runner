"""
Health Check Types and Data Models

Defines types, enums, and data models for health check system.
"""

from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Individual component health result."""

    component_name: str = Field(..., description="Name of the component")
    status: HealthStatus = Field(..., description="Health status")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    details: str = Field(..., description="Detailed health information")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    checked_at: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    is_critical: bool = Field(default=False, description="Whether this is a critical component")

    class Config:
        use_enum_values = True


class HealthCheckResult(BaseModel):
    """Overall health check result."""

    status: HealthStatus = Field(..., description="Overall system health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    components: Dict[str, ComponentHealth] = Field(
        default_factory=dict,
        description="Individual component health results"
    )
    total_components: int = Field(default=0, description="Total number of components checked")
    healthy_components: int = Field(default=0, description="Number of healthy components")
    degraded_components: int = Field(default=0, description="Number of degraded components")
    unhealthy_components: int = Field(default=0, description="Number of unhealthy components")
    response_time_ms: Optional[float] = Field(None, description="Total check duration in milliseconds")
    details: str = Field(default="", description="Additional details about the health check")

    class Config:
        use_enum_values = True


class SystemHealth(HealthCheckResult):
    """Extended system health with aggregation logic."""

    def add_component(self, component: ComponentHealth) -> None:
        """Add a component health result."""
        self.components[component.component_name] = component
        self.total_components += 1

        if component.status == HealthStatus.HEALTHY:
            self.healthy_components += 1
        elif component.status == HealthStatus.DEGRADED:
            self.degraded_components += 1
        elif component.status == HealthStatus.UNHEALTHY:
            self.unhealthy_components += 1

    def calculate_overall_status(self) -> HealthStatus:
        """Calculate overall system health based on component status."""
        # If any critical component is unhealthy, system is unhealthy
        for component in self.components.values():
            if component.is_critical and component.status == HealthStatus.UNHEALTHY:
                self.status = HealthStatus.UNHEALTHY
                self.details = f"Critical component {component.component_name} is unhealthy"
                return self.status

        # If any critical component is degraded, system is degraded
        for component in self.components.values():
            if component.is_critical and component.status == HealthStatus.DEGRADED:
                self.status = HealthStatus.DEGRADED
                self.details = f"Critical component {component.component_name} is degraded"
                return self.status

        # If any component is unhealthy, system is degraded (unless all are healthy)
        if self.unhealthy_components > 0:
            self.status = HealthStatus.DEGRADED
            self.details = f"{self.unhealthy_components} component(s) unhealthy"
            return self.status

        # If any component is degraded, system is degraded
        if self.degraded_components > 0:
            self.status = HealthStatus.DEGRADED
            self.details = f"{self.degraded_components} component(s) degraded"
            return self.status

        # All components healthy
        self.status = HealthStatus.HEALTHY
        self.details = "All components healthy"
        return self.status


class HealthCheckConfig(BaseModel):
    """Configuration for health check execution."""

    timeout_seconds: float = Field(default=5.0, description="Timeout for each health check")
    parallel_execution: bool = Field(default=True, description="Execute checks in parallel")
    cache_ttl_seconds: int = Field(default=60, description="Cache time-to-live in seconds")
    include_non_critical: bool = Field(default=True, description="Include non-critical components")
    critical_only: bool = Field(default=False, description="Only check critical components")

    class Config:
        use_enum_values = True


class HealthHistory(BaseModel):
    """Health check history for trending."""

    timestamp: datetime = Field(..., description="Check timestamp")
    status: HealthStatus = Field(..., description="Health status at this time")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    component_count: int = Field(..., description="Number of components checked")
    unhealthy_count: int = Field(default=0, description="Number of unhealthy components")

    class Config:
        use_enum_values = True
