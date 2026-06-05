#!/usr/bin/env python
"""
Deep Agents Migration Validation Script

This script validates the Deep Agents implementation by comparing
results with the LangGraph implementation to ensure consistency.

Usage:
    python scripts/validate_deepagents_migration.py --run-id <run_id> --test-id <test_definition_id>

Or run comparison for multiple runs:
    python scripts/validate_deepagents_migration.py --compare-runs <run_id_1>,<run_id_2>
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def get_test_run_results(
    run_id: str, session: AsyncSession
) -> Dict[str, Any]:
    """Fetch test run results from database.

    Args:
        run_id: Test run ID
        session: Database session

    Returns:
        Dict with test run results
    """
    from app.models.test_run import TestRun
    from app.models.test_case import TestCase

    # Get test run
    result = await session.execute(
        select(TestRun).where(TestRun.run_id == run_id)
    )
    test_run = result.scalar_one_or_none()

    if not test_run:
        return {"error": f"Test run {run_id} not found"}

    # Get test cases
    cases_result = await session.execute(
        select(TestCase)
        .where(TestCase.run_id == run_id)
        .order_by(TestCase.step_number)
    )
    test_cases = cases_result.scalars().all()

    # Build result dict
    return {
        "run_id": run_id,
        "test_definition_id": test_run.test_definition_id,
        "status": test_run.status,
        "start_time": test_run.start_time,
        "end_time": test_run.end_time,
        "total_duration": test_run.total_duration,
        "total_tests": test_run.total_tests,
        "passed": test_run.passed,
        "failed": test_run.failed,
        "skipped": test_run.skipped,
        "test_cases": [
            {
                "step_number": tc.step_number,
                "description": tc.description,
                "status": tc.status,
                "error": tc.error,
                "screenshot_path": tc.screenshot_path,
            }
            for tc in test_cases
        ],
    }


def validate_result_structure(result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that test result has expected structure.

    Args:
        result: Test result dict

    Returns:
        Dict with validation results
    """
    errors = []
    warnings = []

    # Check required fields
    required_fields = ["run_id", "status", "total_tests", "passed", "failed"]
    for field in required_fields:
        if field not in result:
            errors.append(f"Missing required field: {field}")

    # Check field types
    if "run_id" in result and not isinstance(result["run_id"], str):
        errors.append("run_id must be a string")

    if "status" in result and result["status"] not in ["passed", "failed", "error", "unknown"]:
        errors.append(f"Invalid status: {result['status']}")

    if "total_tests" in result and not isinstance(result["total_tests"], int):
        errors.append("total_tests must be an integer")

    # Check counts consistency
    if "total_tests" in result and "passed" in result and "failed" in result:
        if result["passed"] + result["failed"] > result["total_tests"]:
            warnings.append(
                f"Count inconsistency: passed+failed ({result['passed']+result['failed']}) "
                f"> total_tests ({result['total_tests']})"
            )

    # Check test_cases structure
    if "test_cases" in result:
        if not isinstance(result["test_cases"], list):
            errors.append("test_cases must be a list")
        else:
            for idx, case in enumerate(result["test_cases"]):
                if not isinstance(case, dict):
                    errors.append(f"test_cases[{idx}] must be a dict")
                    continue

                if "step_number" not in case:
                    warnings.append(f"test_cases[{idx}] missing step_number")
                if "status" not in case:
                    warnings.append(f"test_cases[{idx}] missing status")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def compare_results(
    result1: Dict[str, Any], result2: Dict[str, Any], label1: str = "Result 1", label2: str = "Result 2"
) -> Dict[str, Any]:
    """Compare two test results and identify differences.

    Args:
        result1: First test result
        result2: Second test result
        label1: Label for first result
        label2: Label for second result

    Returns:
        Dict with comparison results
    """
    differences = []

    # Compare overall status
    if result1.get("status") != result2.get("status"):
        differences.append({
            "field": "status",
            label1: result1.get("status"),
            label2: result2.get("status"),
        })

    # Compare test counts
    for field in ["total_tests", "passed", "failed", "skipped"]:
        if result1.get(field) != result2.get(field):
            differences.append({
                "field": field,
                label1: result1.get(field),
                label2: result2.get(field),
            })

    # Compare test cases
    cases1 = {c.get("step_number"): c for c in result1.get("test_cases", [])}
    cases2 = {c.get("step_number"): c for c in result2.get("test_cases", [])}

    all_steps = set(cases1.keys()) | set(cases2.keys())

    for step_num in sorted(all_steps):
        case1 = cases1.get(step_num, {})
        case2 = cases2.get(step_num, {})

        if case1.get("status") != case2.get("status"):
            differences.append({
                "field": f"step_{step_num}_status",
                label1: case1.get("status"),
                label2: case2.get("status"),
                "description": case1.get("description", "N/A"),
            })

    return {
        "identical": len(differences) == 0,
        "differences": differences,
    }


async def run_validation(run_id: str, test_definition_id: str) -> Dict[str, Any]:
    """Run validation for a single test execution.

    Args:
        run_id: Test run ID to validate
        test_definition_id: Test definition ID

    Returns:
        Dict with validation results
    """
    logger.info(f"Starting validation for run {run_id}")

    # Get results from filesystem (Deep Agents output)
    results_path = Path(f"/tmp/test_runs/{run_id}/test_results.json")

    if not results_path.exists():
        return {
            "run_id": run_id,
            "valid": False,
            "error": f"Results file not found: {results_path}",
        }

    with open(results_path, "r") as f:
        file_results = json.load(f)

    # Validate structure
    structure_validation = validate_result_structure(file_results)

    # Get results from database
    from app.core.worker_db import run_with_session

    async with run_with_session() as session:
        db_results = await get_test_run_results(run_id, session)

    if "error" in db_results:
        return {
            "run_id": run_id,
            "valid": False,
            "error": db_results["error"],
            "structure_validation": structure_validation,
        }

    # Compare file and DB results
    comparison = compare_results(file_results, db_results, "File", "Database")

    return {
        "run_id": run_id,
        "test_definition_id": test_definition_id,
        "valid": structure_validation["valid"] and comparison["identical"],
        "structure_validation": structure_validation,
        "comparison": comparison,
        "file_results": file_results,
        "db_results": db_results,
    }


async def run_dual_execution_comparison(
    test_definition_id: str, goal: str, url: str
) -> Dict[str, Any]:
    """Run both LangGraph and Deep Agents implementations and compare results.

    Args:
        test_definition_id: Test definition ID
        goal: Test goal
        url: Target URL

    Returns:
        Dict with comparison results
    """
    logger.info(f"Running dual execution comparison for test {test_definition_id}")

    # Create two run IDs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    langgraph_run_id = f"compare_langgraph_{timestamp}"
    deepagents_run_id = f"compare_deepagents_{timestamp}"

    results = {}

    # Run with LangGraph (current implementation)
    try:
        logger.info(f"Running LangGraph execution: {langgraph_run_id}")
        # This would call the existing implementation
        # For now, we'll simulate
        results["langgraph"] = {
            "run_id": langgraph_run_id,
            "status": "simulated",
            "note": "LangGraph execution not yet implemented in this script",
        }
    except Exception as e:
        results["langgraph"] = {"error": str(e)}

    # Run with Deep Agents
    try:
        logger.info(f"Running Deep Agents execution: {deepagents_run_id}")
        # Import and run Deep Agents
        from app.agents.deepagents_test_runner import execute_test_run

        # Mock Playwright page for testing
        from unittest.mock import MagicMock
        mock_page = MagicMock()

        deepagents_result = await execute_test_run(
            goal=goal,
            url=url,
            run_id=deepagents_run_id,
            mode="full_pipeline",
            page=mock_page,
        )

        results["deepagents"] = deepagents_result
    except Exception as e:
        results["deepagents"] = {"error": str(e)}

    # Compare results if both succeeded
    if "error" not in results.get("langgraph", {}) and "error" not in results.get("deepagents", {}):
        comparison = compare_results(
            results["langgraph"],
            results["deepagents"],
            "LangGraph",
            "DeepAgents",
        )
        results["comparison"] = comparison

    return results


def print_validation_report(validation: Dict[str, Any]):
    """Print a formatted validation report.

    Args:
        validation: Validation results dict
    """
    print("\n" + "=" * 60)
    print("DEEP AGENTS MIGRATION VALIDATION REPORT")
    print("=" * 60)

    print(f"\nRun ID: {validation.get('run_id', 'N/A')}")
    print(f"Test Definition ID: {validation.get('test_definition_id', 'N/A')}")

    # Overall validation
    valid = validation.get("valid", False)
    print(f"\nOverall Status: {'✅ VALID' if valid else '❌ INVALID'}")

    # Structure validation
    structure = validation.get("structure_validation", {})
    print(f"\n--- Structure Validation ---")
    print(f"Valid: {'✅ Yes' if structure.get('valid') else '❌ No'}")

    if structure.get("errors"):
        print("Errors:")
        for error in structure["errors"]:
            print(f"  - {error}")

    if structure.get("warnings"):
        print("Warnings:")
        for warning in structure["warnings"]:
            print(f"  - {warning}")

    # Comparison results
    comparison = validation.get("comparison", {})
    print(f"\n--- File vs Database Comparison ---")
    print(f"Identical: {'✅ Yes' if comparison.get('identical') else '❌ No'}")

    if comparison.get("differences"):
        print("Differences:")
        for diff in comparison["differences"]:
            print(f"  - {diff.get('field')}: {diff.get('Result 1')} vs {diff.get('Result 2')}")

    # Summary
    print(f"\n--- Summary ---")
    file_results = validation.get("file_results", {})
    print(f"Total Tests: {file_results.get('total_tests', 'N/A')}")
    print(f"Passed: {file_results.get('passed', 'N/A')}")
    print(f"Failed: {file_results.get('failed', 'N/A')}")

    print("=" * 60)


def print_comparison_report(results: Dict[str, Any]):
    """Print a formatted dual execution comparison report.

    Args:
        results: Comparison results dict
    """
    print("\n" + "=" * 60)
    print("DUAL EXECUTION COMPARISON REPORT")
    print("=" * 60)

    for impl, result in results.items():
        if impl == "comparison":
            continue
        print(f"\n--- {impl.upper()} ---")
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Status: {result.get('status', 'N/A')}")
            print(f"Total Tests: {result.get('total_tests', 'N/A')}")
            print(f"Passed: {result.get('passed', 'N/A')}")
            print(f"Failed: {result.get('failed', 'N/A')}")

    # Comparison
    comparison = results.get("comparison", {})
    if comparison:
        print(f"\n--- Comparison ---")
        print(f"Identical: {'✅ Yes' if comparison.get('identical') else '❌ No'}")

        if comparison.get("differences"):
            print("Differences:")
            for diff in comparison["differences"]:
                print(f"  - {diff.get('field')}: {diff.get('LangGraph')} vs {diff.get('DeepAgents')}")
    else:
        print("\n⚠️  Comparison not available (one or both executions failed)")

    print("=" * 60)


async def main():
    """Main entry point for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate Deep Agents migration"
    )

    parser.add_argument(
        "--run-id",
        help="Test run ID to validate"
    )

    parser.add_argument(
        "--test-id",
        help="Test definition ID"
    )

    parser.add_argument(
        "--compare-runs",
        help="Comma-separated run IDs to compare (e.g., run1,run2)"
    )

    parser.add_argument(
        "--dual-execution",
        action="store_true",
        help="Run both implementations and compare (requires test-id, goal, url)"
    )

    parser.add_argument(
        "--goal",
        help="Test goal (for --dual-execution)"
    )

    parser.add_argument(
        "--url",
        help="Target URL (for --dual-execution)"
    )

    args = parser.parse_args()

    if args.dual_execution:
        # Run dual execution comparison
        if not all([args.test_id, args.goal, args.url]):
            print("Error: --dual-execution requires --test-id, --goal, and --url")
            return 1

        results = await run_dual_execution_comparison(
            args.test_id, args.goal, args.url
        )
        print_comparison_report(results)

    elif args.run_id and args.test_id:
        # Validate single run
        validation = await run_validation(args.run_id, args.test_id)
        print_validation_report(validation)

        # Exit with error code if validation failed
        if not validation.get("valid"):
            return 1

    elif args.compare_runs:
        # Compare multiple runs
        run_ids = args.compare_runs.split(",")
        logger.info(f"Comparing runs: {run_ids}")

        # Would implement multi-run comparison here
        print("Multi-run comparison not yet implemented")

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
