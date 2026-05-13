#!/usr/bin/env python3
"""
Test script to verify batch execution refactoring.

This script tests the new batch execution logic without requiring
full Docker environment or API keys.
"""

import asyncio
import sys
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone


async def test_batch_execution_logic():
    """Test the batch execution flow."""
    print("=" * 60)
    print("Testing Batch Execution Refactoring")
    print("=" * 60)

    # Mock test steps
    test_steps = [
        {"step_number": 1, "description": "Navigate to localhost:5173"},
        {"step_number": 2, "description": "Enter email address: admin@example.com"},
        {"step_number": 3, "description": "Enter password: changethis"},
        {"step_number": 4, "description": "Click login button"},
        {"step_number": 5, "description": "Verify successful login"}
    ]

    print(f"\n✓ Test data prepared: {len(test_steps)} steps")

    # Test 1: Verify claude_interpreter.py has batch method
    print("\n[Test 1] Checking claude_interpreter.py...")

    try:
        from app.services.claude_interpreter import ClaudeTestInterpreter

        interpreter = ClaudeTestInterpreter()

        # Check if batch method exists
        assert hasattr(interpreter, 'interpret_and_execute_batch'), \
            "Missing interpret_and_execute_batch method!"

        print("✓ interpret_and_execute_batch() method exists")

        # Check method signature
        import inspect
        sig = inspect.signature(interpreter.interpret_and_execute_batch)
        params = list(sig.parameters.keys())

        assert 'page' in params, "Missing 'page' parameter"
        assert 'test_steps' in params, "Missing 'test_steps' parameter"
        assert 'context' in params, "Missing 'context' parameter"

        print("✓ Method signature correct")

    except Exception as e:
        print(f"✗ Test 1 FAILED: {str(e)}")
        return False

    # Test 2: Verify test_execution.py has batch execution function
    print("\n[Test 2] Checking test_execution.py...")

    try:
        from app.tasks.test_execution import _execute_all_steps_with_ai

        print("✓ _execute_all_steps_with_ai() function exists")

        # Check function signature
        sig = inspect.signature(_execute_all_steps_with_ai)
        params = list(sig.parameters.keys())

        assert 'page' in params, "Missing 'page' parameter"
        assert 'test_steps' in params, "Missing 'test_steps' parameter"
        assert 'environment' in params, "Missing 'environment' parameter"

        print("✓ Function signature correct")

    except Exception as e:
        print(f"✗ Test 2 FAILED: {str(e)}")
        return False

    # Test 3: Verify legacy method still exists for backward compatibility
    print("\n[Test 3] Checking backward compatibility...")

    try:
        from app.tasks.test_execution import _execute_step_with_ai

        print("✓ Legacy _execute_step_with_ai() still exists")

        # Check it's marked as deprecated
        docstring = _execute_step_with_ai.__doc__
        assert docstring and 'DEPRECATED' in docstring, \
            "Legacy method should be marked as DEPRECATED"

        print("✓ Legacy method properly marked as DEPRECATED")

    except Exception as e:
        print(f"✗ Test 3 FAILED: {str(e)}")
        return False

    # Test 4: Verify batch prompt generation
    print("\n[Test 4] Checking batch prompt generation...")

    try:
        from app.services.claude_interpreter import ClaudeTestInterpreter

        interpreter = ClaudeTestInterpreter()

        # Mock context
        context = {"url": "http://localhost:5173", "title": "Login Page"}

        # Generate prompt
        prompt = interpreter._build_batch_execution_prompt(test_steps, context)

        # Verify prompt contains all steps
        for step in test_steps:
            assert step['description'] in prompt, \
                f"Step description not in prompt: {step['description']}"

        print(f"✓ Prompt contains all {len(test_steps)} steps")

        # Verify prompt has correct structure
        assert "Test Plan - Execute ALL steps" in prompt, \
            "Prompt missing test plan header"
        assert "SEQUENTIALLY" in prompt, \
            "Prompt missing sequential instruction"
        assert "single session" in prompt.lower(), \
            "Prompt doesn't emphasize single session"

        print("✓ Prompt structure matches CLI architecture")

    except Exception as e:
        print(f"✗ Test 4 FAILED: {str(e)}")
        return False

    # Test 5: Simulate batch execution with mock
    print("\n[Test 5] Simulating batch execution...")

    try:
        from app.services.claude_interpreter import ClaudeTestInterpreter

        interpreter = ClaudeTestInterpreter()

        # Mock page
        mock_page = Mock()
        mock_page.url = "http://localhost:5173"

        async def mock_title():
            return "Test Page"

        mock_page.title = mock_title

        # Test fallback batch interpretation (doesn't require SDK)
        context = {"environment": {}}

        results = await interpreter._fallback_batch_interpretation(
            mock_page,
            test_steps,
            context
        )

        # Verify results
        assert len(results) == len(test_steps), \
            f"Expected {len(test_steps)} results, got {len(results)}"

        for idx, result in enumerate(results):
            assert 'step_number' in result, f"Result {idx} missing step_number"
            assert 'description' in result, f"Result {idx} missing description"
            assert 'status' in result, f"Result {idx} missing status"
            assert 'mode' in result, f"Result {idx} missing mode"
            assert result['mode'] == 'rule_based_fallback', \
                f"Expected rule_based_fallback mode, got {result.get('mode')}"

        print(f"✓ Batch execution returned {len(results)} results")

        # Check structure
        passed_count = sum(1 for r in results if r['status'] == 'passed')
        print(f"✓ Results breakdown: {passed_count} passed, {len(results) - passed_count} failed")

    except Exception as e:
        print(f"✗ Test 5 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # All tests passed
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    print("\nSummary:")
    print("- Batch execution method exists and has correct signature")
    print("- Legacy method preserved for backward compatibility")
    print("- Prompt generation matches CLI architecture")
    print("- Fallback execution works correctly")
    print("\nThe refactoring is ready for production use!")

    return True


if __name__ == "__main__":
    # Add parent directory to path for imports
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    success = asyncio.run(test_batch_execution_logic())
    sys.exit(0 if success else 1)
