"""
Schedule Resolver Factory

Factory pattern implementation for creating and managing
schedule resolver strategies with registry support.
"""

import logging
from typing import Dict, List, Optional, Type

from app.models.schedule import Schedule
from app.services.strategies.schedule_resolver_strategy import ScheduleResolverStrategy
from app.services.strategies.single_test_resolver import SingleTestResolver
from app.services.strategies.suite_resolver import SuiteResolver
from app.services.strategies.tag_filter_resolver import TagFilterResolver


logger = logging.getLogger(__name__)


class ScheduleResolverFactory:
    """
    Factory for creating schedule resolver strategies.

    Implements the Registry Pattern to allow dynamic strategy registration.
    This enables the Open/Closed Principle - new strategies can be added
    without modifying existing code.

    Usage:
        # Get strategy for schedule type
        strategy = ScheduleResolverFactory.get_strategy('single')

        # Register custom strategy
        ScheduleResolverFactory.register_strategy('custom', CustomResolver())

        # List available strategies
        strategies = ScheduleResolverFactory.list_strategies()
    """

    # Registry of available strategies
    _strategies: Dict[str, ScheduleResolverStrategy] = {}
    _initialized = False

    @classmethod
    def _initialize_default_strategies(cls) -> None:
        """
        Initialize factory with default strategies.

        This method is called automatically on first use to register
        all built-in schedule resolver strategies.
        """
        if cls._initialized:
            return

        logger.info("Initializing ScheduleResolverFactory with default strategies")

        # Register built-in strategies
        cls.register_strategy('single', SingleTestResolver())
        cls.register_strategy('suite', SuiteResolver())
        cls.register_strategy('tag_filter', TagFilterResolver())

        cls._initialized = True

        logger.info(
            "Registered %d default strategies: %s",
            len(cls._strategies),
            list(cls._strategies.keys())
        )

    @classmethod
    def register_strategy(
        cls,
        schedule_type: str,
        strategy: ScheduleResolverStrategy
    ) -> None:
        """
        Register a new strategy for a schedule type.

        This allows for custom/extension strategies to be added at runtime,
        following the Open/Closed Principle.

        Args:
            schedule_type: Schedule type identifier (e.g., 'custom', 'advanced')
            strategy: Strategy instance to register

        Raises:
            ValueError: If schedule_type is already registered
            TypeError: If strategy is not a ScheduleResolverStrategy instance

        Example:
            ```python
            class CustomResolver(ScheduleResolverStrategy):
                async def resolve(self, schedule, db):
                    # Custom logic here
                    return [1, 2, 3]

                def get_strategy_name(self):
                    return "CustomResolver"

                def get_supported_schedule_types(self):
                    return ['custom']

            factory.register_strategy('custom', CustomResolver())
            ```
        """
        if not isinstance(strategy, ScheduleResolverStrategy):
            raise TypeError(
                f"Strategy must be instance of ScheduleResolverStrategy, "
                f"got {type(strategy).__name__}"
            )

        if schedule_type in cls._strategies:
            logger.warning(
                "Strategy for schedule_type '%s' already registered (%s). "
                "Overwriting with new strategy: %s",
                schedule_type,
                cls._strategies[schedule_type].get_strategy_name(),
                strategy.get_strategy_name()
            )

        cls._strategies[schedule_type] = strategy
        logger.info(
            "Registered strategy '%s' for schedule_type '%s'",
            strategy.get_strategy_name(),
            schedule_type
        )

    @classmethod
    def get_strategy(cls, schedule_type: str) -> ScheduleResolverStrategy:
        """
        Get appropriate strategy for schedule type.

        Args:
            schedule_type: Schedule type identifier

        Returns:
            Strategy instance for the given schedule type

        Raises:
            ValueError: If schedule_type is not registered

        Example:
            ```python
            strategy = factory.get_strategy('single')
            test_ids = await strategy.resolve(schedule, db)
            ```
        """
        # Initialize on first use
        cls._initialize_default_strategies()

        strategy = cls._strategies.get(schedule_type)

        if not strategy:
            available_types = ', '.join(cls._strategies.keys())
            raise ValueError(
                f"Unknown schedule_type: '{schedule_type}'. "
                f"Available types: {available_types}"
            )

        logger.debug(
            "Retrieved strategy '%s' for schedule_type '%s'",
            strategy.get_strategy_name(),
            schedule_type
        )

        return strategy

    @classmethod
    def get_strategy_for_schedule(cls, schedule: Schedule) -> ScheduleResolverStrategy:
        """
        Get appropriate strategy for a schedule object.

        Convenience method that extracts schedule_type from the schedule.

        Args:
            schedule: Schedule object

        Returns:
            Strategy instance for the schedule's type

        Raises:
            ValueError: If schedule_type is not registered
        """
        return cls.get_strategy(schedule.schedule_type)

    @classmethod
    def list_strategies(cls) -> Dict[str, str]:
        """
        List all registered strategies with their descriptions.

        Returns:
            Dictionary mapping schedule_type to strategy description

        Example:
            ```python
            strategies = factory.list_strategies()
            # Returns: {'single': 'SingleTestResolver - ...', ...}
            ```
        """
        # Initialize on first use
        cls._initialize_default_strategies()

        return {
            schedule_type: strategy.get_strategy_description()
            for schedule_type, strategy in cls._strategies.items()
        }

    @classmethod
    def is_strategy_registered(cls, schedule_type: str) -> bool:
        """
        Check if a strategy is registered for a schedule type.

        Args:
            schedule_type: Schedule type identifier

        Returns:
            True if strategy is registered, False otherwise
        """
        # Initialize on first use
        cls._initialize_default_strategies()

        return schedule_type in cls._strategies

    @classmethod
    def unregister_strategy(cls, schedule_type: str) -> bool:
        """
        Unregister a strategy (primarily for testing).

        Args:
            schedule_type: Schedule type identifier to unregister

        Returns:
            True if strategy was removed, False if not found

        Warning:
            This is primarily intended for testing purposes.
            Use with caution in production code.
        """
        if schedule_type in cls._strategies:
            strategy = cls._strategies.pop(schedule_type)
            logger.info(
                "Unregistered strategy '%s' for schedule_type '%s'",
                strategy.get_strategy_name(),
                schedule_type
            )
            return True
        return False

    @classmethod
    def reset(cls) -> None:
        """
        Reset factory to initial state (primarily for testing).

        Removes all registered strategies and resets initialization flag.

        Warning:
            This is primarily intended for testing purposes.
            Use with caution in production code.
        """
        cls._strategies.clear()
        cls._initialized = False
        logger.info("Reset ScheduleResolverFactory to initial state")

    @classmethod
    def _force_initialize(cls) -> None:
        """
        Force initialization without checking _initialized flag.

        This is used internally after reset to ensure proper reinitialization.

        Warning:
            Internal use only - use _initialize_default_strategies() instead.
        """
        logger.info("Force initializing ScheduleResolverFactory")
        cls.register_strategy('single', SingleTestResolver())
        cls.register_strategy('suite', SuiteResolver())
        cls.register_strategy('tag_filter', TagFilterResolver())
        cls._initialized = True
