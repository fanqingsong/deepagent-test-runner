"""
Test management tools for LangGraph agents.

Provides tools for the Planner agent (save plans) and Reviewer agent (read results).
"""

import json
import logging
from typing import Any, Dict, Optional

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@tool
async def save_test_plan(test_definition_id: int, plan_json: str) -> str:
    """Save a generated test plan to the database.

    Args:
        test_definition_id: The test definition ID to associate the plan with.
        plan_json: JSON string with keys: plan_id, steps[], estimated_duration, risk_factors, success_criteria.
    """
    from app.core.worker_db import run_with_session
    from app.models.test_definition import TestDefinition

    plan_data = json.loads(plan_json)

    async def _save(db: AsyncSession):
        result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == test_definition_id)
        )
        test_def = result.scalar_one_or_none()
        if not test_def:
            return f"Test definition {test_definition_id} not found"
        test_def.ai_generated_plan = plan_data
        test_def.plan_generation_status = "generated"
        await db.commit()
        return f"Plan saved for test definition {test_definition_id}"

    try:
        return await run_with_session(_save)
    except Exception as e:
        logger.error("Failed to save plan: %s", e)
        return f"Error saving plan: {str(e)}"


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


TEST_MANAGEMENT_TOOLS = [save_test_plan, get_test_results]
