"""
App Execution Service

Handles test execution and publishing workflows for workspaces.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_workspace import TestWorkspace
from app.models.conversation import ConversationMessage
from app.models.test_definition import TestDefinition
from app.models.test_run import TestRun
from app.models.test_case import TestCase

logger = logging.getLogger(__name__)


class AppExecutionService:
    """Handles test execution and publishing for test workspaces."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_app(self, app_id: int) -> dict:
        """Execute the test plan for an app workspace."""
        from app.services.app.app_workspace_crud import AppWorkspaceCrud
        from app.services.app.app_version_service import AppVersionService

        crud = AppWorkspaceCrud(self.db)
        version_service = AppVersionService(self.db)

        app = await crud.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")

        thread = app.conversation_thread
        if not thread:
            raise ValueError("App has no conversation thread")

        app.status = "generating"
        await self.db.flush()

        # Ensure a draft test_definition exists
        test_def = await version_service.ensure_draft_test_definition(app)

        # Persist version snapshot
        await version_service.persist_steps(app, test_def)

        # Create test run via ExecutionService
        run_id = str(uuid.uuid4())
        from app.services.execution_service import ExecutionService

        exec_svc = ExecutionService(self.db)
        await exec_svc.create_test_run(
            run_id=run_id,
            test_definition_ids=[test_def.id],
            environment=app.test_context.get("environment", {}),
            db=self.db,
        )

        # Dispatch Temporal workflow
        from app.temporal import get_temporal_client
        from app.temporal.workflows.test_execution import TestExecutionWorkflow

        client = await get_temporal_client()

        workflow_result = await client.start_workflow(
            TestExecutionWorkflow.run,
            args=[str(test_def.id), run_id, app.test_context.get("environment", {})],
            id=f"test-execution-{run_id}",
            task_queue="unified-backend-task-queue",
        )

        # Track in job_store
        from app.core.job_store import save_job

        save_job(run_id, {
            "job_id": run_id,
            "status": "running",
            "test_definition_ids": [test_def.id],
            "created_at": datetime.utcnow().isoformat(),
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "results": None,
            "environment": app.test_context.get("environment", {}),
            "workflow_id": workflow_result.id,
            "run_id": workflow_result.run_id,
            "total_steps": 1,
            "completed_steps": [],
            "current_step": 0,
        })

        app.status = "testing"
        app.latest_run_id = run_id
        app.iteration_count += 1
        await self.db.commit()

        return {"job_id": run_id, "run_id": run_id, "status": "running"}

    async def publish_app(self, app_id: int) -> dict:
        """Submit the current draft version for admin review."""
        from app.services.app.app_workspace_crud import AppWorkspaceCrud
        from app.services.app.app_version_service import AppVersionService

        crud = AppWorkspaceCrud(self.db)
        version_service = AppVersionService(self.db)

        app = await crud.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")

        if app.test_definition_id:
            stmt = select(TestDefinition).where(
                TestDefinition.id == app.test_definition_id
            )
            result = await self.db.execute(stmt)
            test_def = result.scalar_one_or_none()
        else:
            test_def = None

        if test_def:
            test_def.name = app.name
            test_def.description = app.description or app.test_goal
            auto_tags = ["app-generated", "submitted", f"app-{app.id}"]
            existing_tags = list(test_def.tags or [])
            for t in auto_tags:
                if t not in existing_tags:
                    existing_tags.append(t)
            test_def.tags = existing_tags
        else:
            test_def = await version_service.ensure_draft_test_definition(app)

        # Get or create the draft version, update snapshot one final time
        draft_version = await version_service.get_or_create_draft_version(app, test_def)
        draft_version.snapshot = await version_service.build_snapshot(app, test_def)
        draft_version.change_description = "Submitted for review"

        # Lock in version number and transition to pending_review
        if draft_version.version == 0:
            # Legacy support: if draft still uses version=0, assign now
            test_def.version += 1
            draft_version.version = test_def.version
        elif draft_version.version > test_def.version:
            # Draft already has a version number, update test_definition.version to match
            test_def.version = draft_version.version
        draft_version.review_status = "pending_review"
        draft_version.rejection_reason = None
        draft_version.created_by = "user"

        test_def.review_status = "pending_review"
        app.status = "pending_review"
        await self.db.commit()
        await self.db.refresh(test_def)

        return {
            "app_id": app.id,
            "test_definition_id": test_def.id,
            "test_id": test_def.test_id,
            "name": test_def.name,
            "status": "pending_review",
            "version_id": draft_version.id,
            "version": draft_version.version,
        }

    async def sync_run_result(self, app_id: int) -> Optional[TestWorkspace]:
        """Sync completed test run results into app state."""
        from app.services.app.app_workspace_crud import AppWorkspaceCrud
        from app.services.app.app_version_service import AppVersionService

        crud = AppWorkspaceCrud(self.db)
        version_service = AppVersionService(self.db)

        app = await crud.get_app(app_id)
        if not app or not app.latest_run_id or app.status != "testing":
            return app

        # Eagerly capture all attributes before any async gap
        latest_run_id = app.latest_run_id
        thread_id = app.conversation_thread.id if app.conversation_thread else None

        from app.core.job_store import get_job

        job = get_job(latest_run_id)
        if not job or job.get("status") != "completed":
            return app

        results = job.get("results", {})
        test_runs = results.get("test_runs", [])

        if test_runs:
            run_data = test_runs[0] if isinstance(test_runs, list) else test_runs
            run_status = run_data.get("status", "unknown")
            passed = run_data.get("passed", 0)
            failed = run_data.get("failed", 0)
            total = run_data.get("total_tests", 0)
            duration = run_data.get("total_duration", 0)

            # Fetch per-step results from test_cases table
            step_results = []
            try:
                stmt = select(TestRun).where(TestRun.run_id == latest_run_id)
                run_row = (await self.db.execute(stmt)).scalar_one_or_none()
                if run_row:
                    tc_stmt = (
                        select(TestCase)
                        .where(TestCase.run_id == run_row.id)
                        .order_by(TestCase.id)
                    )
                    tc_rows = (await self.db.execute(tc_stmt)).scalars().all()
                    for tc in tc_rows:
                        step_results.append({
                            "description": tc.description or f"Step {tc.test_id}",
                            "status": tc.status or "unknown",
                            "duration": tc.duration or 0,
                            "error": tc.error_message or "",
                        })
            except Exception as e:
                logger.warning("Failed to fetch step results for app %s: %s", app_id, e)
                await self.db.rollback()

            app.latest_result = {
                "status": run_status,
                "passed": passed,
                "failed": failed,
                "total": total,
                "duration": duration,
                "run_id": latest_run_id,
                "steps": step_results,
            }

            if run_status == "passed" or (failed == 0 and passed > 0):
                app.status = "passed"
                # Auto-save steps after pass
                if app.test_definition_id:
                    td_stmt = select(TestDefinition).where(
                        TestDefinition.id == app.test_definition_id
                    )
                    td_row = (await self.db.execute(td_stmt)).scalar_one_or_none()
                    if td_row:
                        summary = f"Passed: {passed}/{total} steps"
                        await version_service.persist_steps(app, td_row, run_status="passed", run_summary=summary)
                if thread_id is not None:
                    result_msg = ConversationMessage(
                        thread_id=thread_id,
                        role="assistant",
                        content=f"Test PASSED - {passed}/{total} steps passed ({duration}s)",
                        metadata={
                            "type": "execution_result",
                            "status": "passed",
                            "passed": passed,
                            "failed": failed,
                            "total": total,
                            "duration": duration,
                            "steps": step_results,
                        },
                    )
                    self.db.add(result_msg)
            else:
                app.status = "draft"
                errors = run_data.get("error", "")
                if thread_id is not None:
                    result_msg = ConversationMessage(
                        thread_id=thread_id,
                        role="assistant",
                        content=f"Test FAILED - {passed}/{total} passed, {failed} failed\n{errors}",
                        metadata={
                            "type": "execution_result",
                            "status": "failed",
                            "passed": passed,
                            "failed": failed,
                            "total": total,
                            "duration": duration,
                            "errors": errors,
                            "steps": step_results,
                        },
                    )
                    self.db.add(result_msg)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("sync_run_result commit failed for app %s", app_id)

        return await crud.get_app(app_id)
