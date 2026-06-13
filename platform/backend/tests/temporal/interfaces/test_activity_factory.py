"""
Unit tests for ActivityFactory.

Tests the activity factory pattern implementation.
"""

import pytest
from unittest.mock import Mock, patch

from app.temporal.interfaces.activity_factory import (
    ActivityFactory,
    get_activity_factory,
    register_activity,
    get_activity,
    activity,
)
from app.temporal.interfaces.base_activity import BaseActivity
from app.temporal.interfaces.activity_interface import (
    IActivity,
    ActivityInput,
    ActivityOutput,
)


class MockInput(ActivityInput):
    """Mock input for testing."""

    test_field: str = "test_value"


class MockOutput(ActivityOutput):
    """Mock output for testing."""

    result_field: str = "result_value"


class MockActivity(BaseActivity[MockInput, MockOutput]):
    """Mock activity for testing."""

    async def validate_input(self, input_data: MockInput) -> bool:
        await super().validate_input(input_data)
        return bool(input_data.test_field)

    async def execute_impl(self, input_data: MockInput) -> MockOutput:
        return MockOutput(result_field=f"processed_{input_data.test_field}")


class AnotherMockActivity(BaseActivity[MockInput, MockOutput]):
    """Another mock activity for testing."""

    async def validate_input(self, input_data: MockInput) -> bool:
        await super().validate_input(input_data)
        return True

    async def execute_impl(self, input_data: MockInput) -> MockOutput:
        return MockOutput(result_field="another_processed")


class TestActivityFactory:
    """Test ActivityFactory implementation."""

    def test_factory_singleton(self):
        """Test factory singleton pattern."""
        factory1 = ActivityFactory()
        factory2 = ActivityFactory()

        assert factory1 is factory2

    def test_register_activity(self):
        """Test activity registration."""
        factory = ActivityFactory()

        factory.register_activity("MockActivity", MockActivity, singleton=True)

        assert factory.is_registered("MockActivity")
        assert "MockActivity" in factory.list_activities()

    def test_register_activity_singleton(self):
        """Test singleton registration."""
        factory = ActivityFactory()

        factory.register_activity("MockActivity", MockActivity, singleton=True)

        # Get instance twice
        instance1 = factory.get_activity("MockActivity")
        instance2 = factory.get_activity("MockActivity")

        # Should be same instance (singleton)
        assert instance1 is instance2

    def test_register_activity_non_singleton(self):
        """Test non-singleton registration."""
        factory = ActivityFactory()

        factory.register_activity("MockActivity", MockActivity, singleton=False)

        # Get instance twice
        instance1 = factory.get_activity("MockActivity")
        instance2 = factory.get_activity("MockActivity")

        # Should be different instances (non-singleton)
        assert instance1 is not instance2

    def test_get_activity_force_new_instance(self):
        """Test forcing new instance even for singleton."""
        factory = ActivityFactory()

        factory.register_activity("MockActivity", MockActivity, singleton=True)

        instance1 = factory.get_activity("MockActivity")
        instance2 = factory.get_activity("MockActivity", force_new_instance=True)

        # Should be different instances when forced
        assert instance1 is not instance2

    def test_get_activity_not_registered(self):
        """Test getting non-registered activity raises error."""
        factory = ActivityFactory()

        with pytest.raises(ValueError, match="Activity 'NonExistent' not registered"):
            factory.get_activity("NonExistent")

    def test_unregister_activity(self):
        """Test unregistering activity."""
        factory = ActivityFactory()

        factory.register_activity("MockActivity", MockActivity)
        assert factory.is_registered("MockActivity")

        factory.unregister_activity("MockActivity")
        assert not factory.is_registered("MockActivity")

    def test_unregister_activity_not_registered(self):
        """Test unregistering non-registered activity raises error."""
        factory = ActivityFactory()

        with pytest.raises(ValueError, match="Activity 'NonExistent' not registered"):
            factory.unregister_activity("NonExistent")

    def test_list_activities(self):
        """Test listing all registered activities."""
        factory = ActivityFactory()

        factory.register_activity("MockActivity", MockActivity)
        factory.register_activity("AnotherMockActivity", AnotherMockActivity)

        activities = factory.list_activities()

        assert len(activities) == 2
        assert "MockActivity" in activities
        assert "AnotherMockActivity" in activities

    def test_register_activity_overwrite(self):
        """Test that registering same activity name overwrites."""
        factory = ActivityFactory()

        factory.register_activity("Activity", MockActivity)
        factory.register_activity("Activity", AnotherMockActivity)

        # Should get the second activity
        instance = factory.get_activity("Activity")
        assert isinstance(instance, AnotherMockActivity)

    def test_create_activity_with_dependencies(self):
        """Test creating activity with dependency injection."""

        class ActivityWithDeps(BaseActivity[MockInput, MockOutput]):
            def __init__(self, dependency1: str, dependency2: int):
                super().__init__()
                self.dependency1 = dependency1
                self.dependency2 = dependency2

            async def validate_input(self, input_data: MockInput) -> bool:
                return True

            async def execute_impl(self, input_data: MockInput) -> MockOutput:
                return MockOutput(result_field=f"{self.dependency1}_{self.dependency2}")

        factory = ActivityFactory()
        activity = factory.create_activity(
            ActivityWithDeps,
            dependency1="test",
            dependency2=123,
        )

        assert isinstance(activity, ActivityWithDeps)
        assert activity.dependency1 == "test"
        assert activity.dependency2 == 123


class TestGlobalFactoryFunctions:
    """Test global factory convenience functions."""

    def test_get_activity_factory_singleton(self):
        """Test global factory singleton."""
        factory1 = get_activity_factory()
        factory2 = get_activity_factory()

        assert factory1 is factory2

    def test_register_activity_global(self):
        """Test global register_activity function."""
        factory = get_activity_factory()

        register_activity("MockActivity", MockActivity)

        assert factory.is_registered("MockActivity")

    def test_get_activity_global(self):
        """Test global get_activity function."""
        factory = get_activity_factory()

        register_activity("MockActivity", MockActivity)

        activity = get_activity("MockActivity")

        assert isinstance(activity, MockActivity)


class TestActivityDecorator:
    """Test @activity decorator."""

    def test_activity_decorator_default_name(self):
        """Test @activity decorator with default name."""
        factory = get_activity_factory()

        @activity()
        class DecoratedActivity(BaseActivity[MockInput, MockOutput]):
            async def validate_input(self, input_data: MockInput) -> bool:
                return True

            async def execute_impl(self, input_data: MockInput) -> MockOutput:
                return MockOutput(result_field="decorated")

        # Should be registered with class name
        assert factory.is_registered("DecoratedActivity")

        activity_instance = get_activity("DecoratedActivity")
        assert isinstance(activity_instance, DecoratedActivity)

    def test_activity_decorator_custom_name(self):
        """Test @activity decorator with custom name."""
        factory = get_activity_factory()

        @activity(name="CustomActivity")
        class DecoratedActivity(BaseActivity[MockInput, MockOutput]):
            async def validate_input(self, input_data: MockInput) -> bool:
                return True

            async def execute_impl(self, input_data: MockInput) -> MockOutput:
                return MockOutput(result_field="decorated")

        # Should be registered with custom name
        assert factory.is_registered("CustomActivity")

        activity_instance = get_activity("CustomActivity")
        assert isinstance(activity_instance, DecoratedActivity)

    def test_activity_decorator_non_singleton(self):
        """Test @activity decorator with non-singleton."""
        factory = get_activity_factory()

        @activity(singleton=False)
        class DecoratedActivity(BaseActivity[MockInput, MockOutput]):
            async def validate_input(self, input_data: MockInput) -> bool:
                return True

            async def execute_impl(self, input_data: MockInput) -> MockOutput:
                return MockOutput(result_field="decorated")

        # Should create new instances
        instance1 = get_activity("DecoratedActivity")
        instance2 = get_activity("DecoratedActivity")

        assert instance1 is not instance2


class TestActivityFactoryWithRealActivities:
    """Test factory with real activity execution."""

    @pytest.mark.asyncio
    async def test_factory_activity_execution(self):
        """Test executing activity obtained from factory."""
        factory = get_activity_factory()

        register_activity("MockActivity", MockActivity)

        activity = get_activity("MockActivity")
        input_data = MockInput(test_field="test_value")

        output = await activity.execute(input_data)

        assert output.result_field == "processed_test_value"

    @pytest.mark.asyncio
    async def test_factory_activity_validation(self):
        """Test validation through factory activity."""
        factory = get_activity_factory()

        register_activity("MockActivity", MockActivity)

        activity = get_activity("MockActivity")
        input_data = MockInput(test_field="")  # Invalid

        with pytest.raises(ValueError):
            await activity.execute(input_data)

    @pytest.mark.asyncio
    async def test_factory_multiple_activities(self):
        """Test factory with multiple activities."""
        factory = get_activity_factory()

        register_activity("MockActivity", MockActivity)
        register_activity("AnotherMockActivity", AnotherMockActivity)

        activity1 = get_activity("MockActivity")
        activity2 = get_activity("AnotherMockActivity")

        input_data = MockInput(test_field="test")

        output1 = await activity1.execute(input_data)
        output2 = await activity2.execute(input_data)

        assert output1.result_field == "processed_test"
        assert output2.result_field == "another_processed"
