"""
Schedule Resolver Strategy Interface

Defines the abstract base class for all schedule resolver strategies.
Following the Strategy Pattern and Open/Closed Principle.
"""

from abc import ABC, abstractmethod
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule


class ScheduleResolverStrategy(ABC):
    """
    Abstract base class for schedule resolution strategies.

    Each strategy implements a specific schedule type resolution logic:
    - 'single': Resolve single test definition
    - 'suite': Resolve test suite to multiple test definitions
    - 'tag_filter': Resolve tests matching specific tags
    - Custom strategies can be added by extending this class

    The strategy pattern allows for:
    1. Open/Closed Principle: Open for extension, closed for modification
    2. Single Responsibility: Each strategy handles one schedule type
    3. Testability: Each strategy can be tested independently
    4. Extensibility: New strategies can be added without modifying existing code
    """

    @abstractmethod
    async def resolve(
        self,
        schedule: Schedule,
        db: AsyncSession
    ) -> List[int]:
        """
        Resolve schedule to test definition IDs.

        Args:
            schedule: Schedule object containing schedule configuration
            db: Async database session for queries

        Returns:
            List of test definition IDs to execute

        Raises:
            ValueError: If required data is missing or invalid
            NotImplementedError: If the strategy is not fully implemented
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get the human-readable name of this strategy.

        Returns:
            Strategy name for logging and debugging
        """
        pass

    @abstractmethod
    def get_supported_schedule_types(self) -> List[str]:
        """
        Get list of schedule types supported by this strategy.

        Returns:
            List of schedule type identifiers (e.g., ['single'])
        """
        pass

    def validate_schedule(self, schedule: Schedule) -> None:
        """
        Validate that schedule contains required data for this strategy.

        Override this method in concrete strategies to perform
        type-specific validation.

        Args:
            schedule: Schedule to validate

        Raises:
            ValueError: If schedule is missing required data
        """
        pass

    def get_strategy_description(self) -> str:
        """
        Get detailed description of this strategy.

        Returns:
            Strategy description for documentation
        """
        return f"{self.get_strategy_name()} - Resolves schedules of type: {', '.join(self.get_supported_schedule_types())}"
