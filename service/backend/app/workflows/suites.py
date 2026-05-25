# service/backend/app/workflows/suites.py
"""
Workflow for test suite execution.
"""
import asyncio
import logging
from datetime import timedelta
from typing import List, Dict, Any
from temporalio import workflow

from app.activities import get_default_retry_policy
from app.workflows.test_execution import TestExecutionWorkflow

logger = logging.getLogger(__name__)


@workflow.defn(sandboxed=False)
class SuiteExecutionWorkflow:
    """
    Workflow for executing a test suite (multiple tests).

    Executes tests in parallel up to a concurrency limit.
    """

    @workflow.run
    async def run(
        self,
        test_suite_id: str,
        test_definition_ids: List[str],
        environment: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute all tests in a suite.

        Args:
            test_suite_id: ID of the test suite
            test_definition_ids: List of test definition IDs to execute
            environment: Optional environment variables

        Returns:
            Dict with suite execution results
        """
        if environment is None:
            environment = {}

        logger.info(f"Starting suite execution for {test_suite_id} with {len(test_definition_ids)} tests")

        # Execute tests in parallel (up to 5 concurrent)
        max_concurrency = 5
        results = []

        for i in range(0, len(test_definition_ids), max_concurrency):
            batch = test_definition_ids[i:i + max_concurrency]

            # Execute batch in parallel
            tasks = [
                workflow.execute_child_workflow(
                    TestExecutionWorkflow.run,
                    test_definition_id=test_id,
                    run_id=f"suite-{test_suite_id}-test-{test_id}",
                    environment=environment
                )
                for test_id in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

        # Aggregate results
        total_tests = len(test_definition_ids)
        passed_tests = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "passed")
        failed_tests = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "failed")

        logger.info(f"Suite execution completed: {passed_tests}/{total_tests} passed")

        return {
            "test_suite_id": test_suite_id,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "results": results
        }
