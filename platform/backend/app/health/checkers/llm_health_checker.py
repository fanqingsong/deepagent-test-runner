"""
LLM Health Checker

Monitors LLM API availability and performance.
"""

import time
import os
from typing import Optional

from app.core.interfaces.health_check_interface import IHealthChecker
from app.core.health_check_types import ComponentHealth, HealthStatus
from app.core.agent_config import get_llm


class LLMHealthChecker(IHealthChecker):
    """
    Health checker for LLM API.

    Checks:
    - LLM API connectivity
    - Basic model invocation
    - Response time
    - Token usage
    - Model availability
    """

    def __init__(self, timeout: float = 10.0):
        """
        Initialize LLM health checker.

        Args:
            timeout: API call timeout in seconds
        """
        self.timeout = timeout

    async def check_health(self) -> ComponentHealth:
        """
        Perform LLM health check.

        Returns:
            ComponentHealth: LLM health status with details
        """
        start_time = time.time()
        metadata = {}

        try:
            # Check if API key is configured
            api_key = os.getenv("LLM_API_KEY")
            if not api_key:
                return ComponentHealth(
                    component_name=self.get_check_type(),
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=round((time.time() - start_time) * 1000, 2),
                    details="LLM_API_KEY not configured",
                    metadata=metadata,
                    is_critical=self.is_critical(),
                )

            # Get model name
            model_name = os.getenv("LLM_MODEL", "glm-4-plus")

            # Create LLM instance
            llm = get_llm(
                model_name=model_name,
                temperature=0.1,
                max_tokens=10,  # Minimal tokens for health check
                timeout=self.timeout,
            )

            # Test with a simple prompt
            test_prompt = "Respond with just 'OK' if you receive this."
            invoke_start = time.time()

            response = await llm.ainvoke([("human", test_prompt)])

            invoke_time = (time.time() - invoke_start) * 1000
            total_time = (time.time() - start_time) * 1000

            # Check response
            if response and hasattr(response, 'content'):
                content = response.content
                metadata = {
                    "model_name": model_name,
                    "response_length": len(content) if content else 0,
                    "invoke_time_ms": round(invoke_time, 2),
                    "base_url": os.getenv("LLM_BASE_URL", "unknown"),
                }

                # Determine health based on response time
                if total_time > 5000:  # More than 5 seconds is degraded
                    return ComponentHealth(
                        component_name=self.get_check_type(),
                        status=HealthStatus.DEGRADED,
                        response_time_ms=round(total_time, 2),
                        details=f"LLM response slow: {total_time:.2f}ms",
                        metadata=metadata,
                        is_critical=self.is_critical(),
                    )

                return ComponentHealth(
                    component_name=self.get_check_type(),
                    status=HealthStatus.HEALTHY,
                    response_time_ms=round(total_time, 2),
                    details="LLM API successful",
                    metadata=metadata,
                    is_critical=self.is_critical(),
                )
            else:
                return ComponentHealth(
                    component_name=self.get_check_type(),
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=round(total_time, 2),
                    details="LLM returned invalid response",
                    metadata=metadata,
                    is_critical=self.is_critical(),
                )

        except Exception as e:
            return ComponentHealth(
                component_name=self.get_check_type(),
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round((time.time() - start_time) * 1000, 2),
                details=f"LLM API call failed: {str(e)}",
                metadata=metadata,
                is_critical=self.is_critical(),
            )

    def get_check_type(self) -> str:
        """Get checker type identifier."""
        return "llm"

    def is_critical(self) -> bool:
        """LLM is important but not critical (system can degrade gracefully)."""
        return False

    def get_timeout_seconds(self) -> float:
        """Get timeout for LLM health check."""
        return self.timeout
