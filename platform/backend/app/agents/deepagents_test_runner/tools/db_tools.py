"""
Database tools for Test Runner agent.

Tools for reading results and persisting scripts.
"""

import json
import logging

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@tool
async def get_test_results(run_id: str) -> str:
    """Get test execution results for a given run_id.

    Returns JSON string with test run summary and individual step results.
    """
    from app.core.worker_db import run_with_session
    from app.models.test_run import TestRun
    from app.models.test_case import TestCase

    async def _get(db: AsyncSession):
        run_result = await db.execute(
            select(TestRun).where(TestRun.run_id == run_id)
        )
        test_run = run_result.scalar_one_or_none()
        if not test_run:
            return json.dumps({"error": f"Run {run_id} not found"})

        cases_result = await db.execute(
            select(TestCase).where(TestCase.run_id == test_run.id)
        )
        cases = cases_result.scalars().all()

        return json.dumps({
            "run_id": run_id,
            "status": test_run.status,
            "total_tests": test_run.total_tests,
            "passed": test_run.passed,
            "failed": test_run.failed,
            "total_duration_ms": test_run.total_duration_ms,
            "steps": [
                {
                    "test_id": c.test_id,
                    "description": c.description,
                    "status": c.status,
                    "duration": c.duration,
                    "error": c.error,
                }
                for c in cases
            ]
        })

    try:
        return await run_with_session(_get)
    except Exception as e:
        logger.error("Failed to get results: %s", e)
        return json.dumps({"error": str(e)})


@tool
async def save_generated_script(
    test_definition_id: int,
    script: str,
    script_status: str,
    metadata_json: str = "{}",
) -> str:
    """Save generated Playwright script to the test definition in database.

    Args:
        test_definition_id: The test definition ID to update.
        script: The generated Playwright script source code.
        script_status: One of "validated", "draft", or "failed".
        metadata_json: Optional JSON string with metadata (validation errors etc).
    """
    from app.core.worker_db import run_with_session
    from app.models.test_definition import TestDefinition

    async def _save(db: AsyncSession):
        result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == test_definition_id)
        )
        test_def = result.scalar_one_or_none()
        if not test_def:
            return f"Test definition {test_definition_id} not found"
        test_def.playwright_script = script
        test_def.script_status = script_status
        test_def.script_metadata = json.loads(metadata_json) if metadata_json else {}
        test_def.execution_mode = "script"
        await db.commit()
        return f"Script saved with status '{script_status}'"

    try:
        return await run_with_session(_save)
    except Exception as e:
        logger.error("Failed to save script: %s", e)
        return f"Error saving script: {str(e)}"
