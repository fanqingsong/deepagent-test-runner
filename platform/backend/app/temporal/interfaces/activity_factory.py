"""
Activity Factory

Factory pattern implementation for creating activity instances.
Provides type-safe activity creation and registration.
"""

import logging
from typing import Any, Dict, Type, TypeVar, Generic, Callable, Optional

from .activity_interface import IActivity, ActivityInput, ActivityOutput
from .base_activity import BaseActivity

InputType = TypeVar("InputType", bound=ActivityInput)
OutputType = TypeVar("OutputType", bound=ActivityOutput)
ActivityType = TypeVar("ActivityType", bound=IActivity)


class ActivityFactory:
    """
    Factory for creating activity instances.

    This factory provides:
    - Type-safe activity creation
    - Activity registration and discovery
    - Singleton pattern for activity instances
    - Dependency injection support
    """

    _instance: Optional["ActivityFactory"] = None
    _activities: Dict[str, Type[IActivity]] = {}
    _singletons: Dict[str, IActivity] = {}

    def __new__(cls) -> "ActivityFactory":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._logger = logging.getLogger("ActivityFactory")
        return cls._instance

    def register_activity(
        self,
        activity_name: str,
        activity_class: Type[IActivity],
        singleton: bool = True,
    ) -> None:
        """
        Register an activity class with the factory.

        Args:
            activity_name: Unique name for the activity
            activity_class: Activity class to register
            singleton: Whether to use singleton pattern (default: True)
        """
        if activity_name in self._activities:
            self._logger.warning(
                f"Activity {activity_name} already registered, overwriting"
            )

        self._activities[activity_name] = activity_class
        self._logger.info(f"Registered activity: {activity_name}")

        if singleton:
            # Pre-create singleton instance
            self._singletons[activity_name] = activity_class()

    def get_activity(
        self,
        activity_name: str,
        force_new_instance: bool = False,
    ) -> IActivity:
        """
        Get an activity instance by name.

        Args:
            activity_name: Name of the activity to retrieve
            force_new_instance: Force creation of new instance (ignore singleton)

        Returns:
            Activity instance

        Raises:
            ValueError: If activity is not registered
        """
        if activity_name not in self._activities:
            raise ValueError(
                f"Activity '{activity_name}' not registered. "
                f"Available activities: {list(self._activities.keys())}"
            )

        # Return singleton if available and not forcing new instance
        if not force_new_instance and activity_name in self._singletons:
            return self._singletons[activity_name]

        # Create new instance
        activity_class = self._activities[activity_name]
        return activity_class()

    def create_activity(
        self,
        activity_class: Type[ActivityType],
        **kwargs: Any,
    ) -> ActivityType:
        """
        Create a new activity instance with dependency injection.

        Args:
            activity_class: Activity class to instantiate
            **kwargs: Dependencies to inject

        Returns:
            Activity instance
        """
        self._logger.debug(f"Creating activity instance: {activity_class.__name__}")
        return activity_class(**kwargs)

    def list_activities(self) -> list[str]:
        """
        List all registered activity names.

        Returns:
            List of activity names
        """
        return list(self._activities.keys())

    def is_registered(self, activity_name: str) -> bool:
        """
        Check if an activity is registered.

        Args:
            activity_name: Name of the activity to check

        Returns:
            True if activity is registered
        """
        return activity_name in self._activities

    def unregister_activity(self, activity_name: str) -> None:
        """
        Unregister an activity from the factory.

        Args:
            activity_name: Name of the activity to unregister

        Raises:
            ValueError: If activity is not registered
        """
        if activity_name not in self._activities:
            raise ValueError(f"Activity '{activity_name}' not registered")

        del self._activities[activity_name]
        if activity_name in self._singletons:
            del self._singletons[activity_name]

        self._logger.info(f"Unregistered activity: {activity_name}")


# Global factory instance
_factory_instance: Optional[ActivityFactory] = None


def get_activity_factory() -> ActivityFactory:
    """
    Get the global activity factory instance.

    Returns:
        ActivityFactory singleton instance
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ActivityFactory()
    return _factory_instance


def register_activity(
    activity_name: str,
    activity_class: Type[IActivity],
    singleton: bool = True,
) -> None:
    """
    Register an activity with the global factory.

    This is a convenience function for registering activities without
    directly accessing the factory instance.

    Args:
        activity_name: Unique name for the activity
        activity_class: Activity class to register
        singleton: Whether to use singleton pattern (default: True)
    """
    factory = get_activity_factory()
    factory.register_activity(activity_name, activity_class, singleton)


def get_activity(activity_name: str, force_new_instance: bool = False) -> IActivity:
    """
    Get an activity instance from the global factory.

    This is a convenience function for retrieving activities without
    directly accessing the factory instance.

    Args:
        activity_name: Name of the activity to retrieve
        force_new_instance: Force creation of new instance

    Returns:
        Activity instance
    """
    factory = get_activity_factory()
    return factory.get_activity(activity_name, force_new_instance)


# Activity decorator for automatic registration
def activity(name: Optional[str] = None, singleton: bool = True):
    """
    Decorator to automatically register an activity class.

    Usage:
        @activity()
        class MyActivity(BaseActivity):
            pass

    Args:
        name: Optional activity name (defaults to class name)
        singleton: Whether to use singleton pattern (default: True)
    """

    def decorator(activity_class: Type[IActivity]) -> Type[IActivity]:
        activity_name = name or activity_class.__name__
        register_activity(activity_name, activity_class, singleton)
        return activity_class

    return decorator
