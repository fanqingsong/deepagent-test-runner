"""
Execution Strategy Pattern Implementation

This module defines the strategy interface for test execution modes,
following the SOLID Open/Closed Principle.

New execution modes can be added without modifying existing code,
simply by implementing the ExecutionStrategy interface and registering
with the ExecutionStrategyFactory.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from playwright.async_api import Page

import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """
    Context object passed to execution strategies.

    Contains all necessary information for test execution
    without coupling strategies to specific implementation details.
    """
    run_id: str
    test_definition_id: str
    page: Page
    url: Optional[str]
    test_goal: Optional[str]
    test_steps: List[Dict[str, Any]]
    environment: Dict[str, Any]
    mode: str
    playwright_script: Optional[str]
    script_status: Optional[str]

    # Additional context for extensibility
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExecutionResult:
    """
    Standardized result object returned by all execution strategies.

    Ensures consistent output format regardless of execution mode.
    """
    run_id: str
    test_definition_id: str
    status: str
    test_cases: List[Dict[str, Any]]
    error: Optional[str]
    start_time: int
    end_time: int
    total_duration: int
    total_tests: int
    passed: int
    failed: int
    skipped: int

    # Additional metrics for extensibility
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "test_definition_id": self.test_definition_id,
            "status": self.status,
            "test_cases": self.test_cases,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration": self.total_duration,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "metadata": self.metadata,
        }


class ExecutionStrategy(ABC):
    """
    Abstract base class for execution strategies.

    All execution strategies must inherit from this class and implement
    the execute method. This ensures consistent interface and behavior
    across different execution modes.

    Example:
        class CustomExecutionStrategy(ExecutionStrategy):
            async def execute(self, context: ExecutionContext) -> ExecutionResult:
                # Custom execution logic
                pass

            @staticmethod
            def can_handle(execution_mode: str) -> bool:
                return execution_mode == "custom"
    """

    @classmethod
    @abstractmethod
    def can_handle(cls, execution_mode: str, script_status: Optional[str] = None) -> bool:
        """
        Determine if this strategy can handle the given execution mode.

        Args:
            execution_mode: The execution mode to check
            script_status: Optional script status for validation

        Returns:
            bool: True if this strategy can handle the execution mode
        """
        pass

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute the test using this strategy's specific logic.

        Args:
            context: ExecutionContext with all necessary execution data

        Returns:
            ExecutionResult with standardized execution results

        Raises:
            Exception: If execution fails (will be caught and handled)
        """
        pass

    def validate_context(self, context: ExecutionContext) -> None:
        """
        Validate execution context before execution.

        Override this method to add strategy-specific validation.
        Raises ValueError if context is invalid.

        Args:
            context: ExecutionContext to validate

        Raises:
            ValueError: If context is invalid for this strategy
        """
        if not context.run_id:
            raise ValueError("run_id is required")
        if not context.test_definition_id:
            raise ValueError("test_definition_id is required")
        if not context.page:
            raise ValueError("page is required")

    def create_error_result(
        self,
        context: ExecutionContext,
        error_message: str,
        start_time: int,
    ) -> ExecutionResult:
        """
        Create a standardized error result.

        Helper method for consistent error handling across strategies.

        Args:
            context: ExecutionContext with execution details
            error_message: Error message to include
            start_time: Execution start timestamp

        Returns:
            ExecutionResult with error status
        """
        end_time = int(datetime.utcnow().timestamp() * 1000)

        return ExecutionResult(
            run_id=context.run_id,
            test_definition_id=context.test_definition_id,
            status="error",
            test_cases=[],
            error=error_message,
            start_time=start_time,
            end_time=end_time,
            total_duration=end_time - start_time,
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
        )
