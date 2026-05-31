"""
Regression Service

Handles saving a successful test run as a reusable regression test definition.
"""

import logging
import random
import time
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import TestDefinition, TestStep, TestRun, TestCase

logger = logging.getLogger(__name__)


class RegressionService:
    """
    Service for managing regression test definitions.

    Converts a passed test run into a reusable regression test definition
    with its successful steps preserved as test steps.
    """

    @staticmethod
    async def save_as_regression(
        db: AsyncSession,
        run_id: str,
        user_id: int,
    ) -> TestDefinition:
        """
        Save a passed test run as a reusable regression test definition.

        Args:
            db: Async database session
            run_id: The string run identifier (TestRun.run_id)
            user_id: ID of the user creating the regression test

        Returns:
            The newly created TestDefinition

        Raises:
            ValueError: If the run is not found or did not pass
        """
        # 1. Load the test run by run_id string
        run_result = await db.execute(
            select(TestRun).where(TestRun.run_id == run_id)
        )
        test_run = run_result.scalar_one_or_none()

        if not test_run:
            raise ValueError(f"Test run '{run_id}' not found")

        if test_run.status != "passed":
            raise ValueError(
                f"Cannot create regression from run '{run_id}': "
                f"status is '{test_run.status}', expected 'passed'"
            )

        # 2. Load associated test cases using the run's primary key ID
        cases_result = await db.execute(
            select(TestCase)
            .where(TestCase.run_id == test_run.id)
            .order_by(TestCase.id)
        )
        test_cases = cases_result.scalars().all()

        # 3. Load the original test definition
        if not test_run.test_definition_id:
            raise ValueError(
                f"Test run '{run_id}' has no associated test definition"
            )

        original_result = await db.execute(
            select(TestDefinition).where(
                TestDefinition.id == test_run.test_definition_id
            )
        )
        original = original_result.scalar_one_or_none()

        if not original:
            raise ValueError(
                f"Original test definition {test_run.test_definition_id} not found"
            )

        # 4. Create new TestDefinition
        regression_tags = list(original.tags or [])
        if "regression" not in regression_tags:
            regression_tags.append("regression")

        unique_test_id = f"reg-{int(time.time())}-{random.randint(1000, 9999)}"

        new_definition = TestDefinition(
            name=f"[Regression] {original.name}",
            description=original.description,
            test_id=unique_test_id,
            url=original.url,
            environment=original.environment or {},
            tags=regression_tags,
            test_goal=original.test_goal,
            test_context=original.test_context or {},
            plan_generation_status="approved",
            ai_generated_plan=original.ai_generated_plan or {},
            plan_metadata={"regression_source": run_id},
            is_regression=True,
            regression_source_run_id=run_id,
            created_by=user_id,
        )

        db.add(new_definition)
        await db.flush()

        logger.info(
            "Created regression definition id=%d test_id=%s from run %s",
            new_definition.id,
            unique_test_id,
            run_id,
        )

        # 6. Create TestStep records from passing test cases
        passing_cases = [
            case for case in test_cases if case.status == "passed"
        ]

        for idx, case in enumerate(passing_cases):
            step_number = idx + 1
            step = TestStep(
                test_definition_id=new_definition.id,
                step_number=step_number,
                description=case.description or f"Step {step_number}",
                type="ai_generated",
                params={},
                expected_result=None,
                is_ai_generated=True,
            )
            db.add(step)

        logger.info(
            "Created %d test steps for regression definition %d",
            len(passing_cases),
            new_definition.id,
        )

        # 7. Commit and return with relationships loaded
        await db.commit()

        result = await db.execute(
            select(TestDefinition)
            .options(selectinload(TestDefinition.test_steps))
            .where(TestDefinition.id == new_definition.id)
        )
        return result.scalar_one()

    @staticmethod
    async def list_regression_tests(
        db: AsyncSession,
    ) -> List[TestDefinition]:
        """
        List all regression test definitions.

        Args:
            db: Async database session

        Returns:
            List of TestDefinition where is_regression is True
        """
        result = await db.execute(
            select(TestDefinition)
            .options(selectinload(TestDefinition.test_steps))
            .where(TestDefinition.is_regression == True)  # noqa: E712
            .order_by(TestDefinition.created_at.desc())
        )
        return list(result.scalars().all())
