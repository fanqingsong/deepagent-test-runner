"""
Conftest for activity unit tests.

This conftest avoids importing the main app which requires temporalio.
Activity tests use mocking and don't need the full app stack.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
import sys
import asyncio

# Mock temporalio before any imports
mock_temporalio = MagicMock()
mock_temporalio.activity = MagicMock()

# Mock the activity.defn decorator to pass through async functions
def mock_activity_defn(func):
    """Mock activity.defn decorator that preserves async functions."""
    return func

mock_temporalio.activity.defn = mock_activity_defn

sys.modules['temporalio'] = mock_temporalio
sys.modules['temporalio.activity'] = mock_temporalio.activity
sys.modules['temporalio.client'] = MagicMock()
sys.modules['temporalio.worker'] = MagicMock()
sys.modules['temporalio.workflow'] = MagicMock()


@pytest.fixture
def mock_temporal_modules():
    """Ensure temporal modules are mocked for all tests."""
    # The mocks are already set up at module level
    yield
