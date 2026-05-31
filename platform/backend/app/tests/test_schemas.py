import pytest
from pydantic import ValidationError

from app.schemas.test_suites import TestSuiteCreate, TestSuiteUpdate


def test_test_suite_create_valid():
    """Test valid TestSuiteCreate schema"""
    data = {
        "name": "Regression Suite",
        "description": "Core regression tests",
        "test_definition_ids": [1, 2, 3],
        "tags": {"category": "regression"}
    }

    suite = TestSuiteCreate(**data)
    assert suite.name == "Regression Suite"
    assert len(suite.test_definition_ids) == 3
    assert suite.tags["category"] == "regression"


def test_test_suite_create_empty_name_fails():
    """Test that empty name fails validation"""
    data = {
        "name": "",
        "test_definition_ids": [1]
    }

    with pytest.raises(ValidationError):
        TestSuiteCreate(**data)


def test_test_suite_create_empty_test_ids_fails():
    """Test that empty test_definition_ids fails validation"""
    data = {
        "name": "Test Suite",
        "test_definition_ids": []
    }

    with pytest.raises(ValidationError):
        TestSuiteCreate(**data)


def test_test_suite_update_partial():
    """Test partial update with TestSuiteUpdate"""
    data = {
        "name": "Updated Name"
    }

    update = TestSuiteUpdate(**data)
    assert update.name == "Updated Name"
    assert update.description is None
    assert update.test_definition_ids is None
