"""
App Service — orchestration layer for the LLM-APP-style test workspace.

Coordinates ExecutionService, conversation models, and
Temporal workflows to provide the generate → execute → refine/publish workflow.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.app import App
from app.models.conversation import ConversationMessage, ConversationThread
from app.models.test_definition import TestDefinition

logger = logging.getLogger(__name__)


class AppService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    async def _ensure_draft_test_definition(self, app: App) -> "TestDefinition":
        """Return the linked draft TestDefinition, creating one if needed."""
        test_def = None
        if app.test_definition_id:
            stmt = select(TestDefinition).where(
                TestDefinition.id == app.test_definition_id
            )
            result = await self.db.execute(stmt)
            test_def = result.scalar_one_or_none()

        if not test_def:
            test_def = TestDefinition(
                name=f"[APP] {app.name}",
                description=app.description or app.test_goal,
                test_id=f"app-{app.id}-{uuid.uuid4().hex[:8]}",
                url=app.url,
                test_goal=app.test_goal,
                test_context=app.test_context,
                environment={},
                tags=["app-generated"],
                is_active=True,
                is_draft=True,
                source_app_id=app.id,
                created_by=app.created_by,
            )
            self.db.add(test_def)
            await self.db.flush()
            app.test_definition_id = test_def.id
        else:
            test_def.test_goal = app.test_goal
            test_def.url = app.url

        await self.db.flush()
        return test_def

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_app(self, user_id: int, data: dict) -> App:
        thread = ConversationThread(
            thread_type="planning",
            status="active",
            created_by=user_id,
            metadata={"source": "app_workspace"},
        )
        self.db.add(thread)
        await self.db.flush()

        app = App(
            name=data.get("name") or "未命名测试",
            description=data.get("description"),
            url=data.get("url") or "",
            test_goal=data.get("test_goal") or "",
            test_context=data.get("test_context", {}),
            icon=data.get("icon", "test-tube"),
            color=data.get("color", "#0f62fe"),
            status="draft",
            created_by=user_id,
            conversation_thread_id=thread.id,
        )
        self.db.add(app)
        await self.db.flush()

        system_msg = ConversationMessage(
            thread_id=thread.id,
            role="system",
            content=f"Created APP: {app.name}\nTarget: {app.url}\nGoal: {app.test_goal}",
            metadata={"type": "app_created", "app_id": app.id},
        )
        self.db.add(system_msg)
        await self.db.commit()
        return await self.get_app(app.id)

    async def get_app(self, app_id: int) -> Optional[App]:
        stmt = (
            select(App)
            .options(
                selectinload(App.conversation_thread).selectinload(
                    ConversationThread.messages
                ),
                selectinload(App.test_definition),
            )
            .where(App.id == app_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_apps(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[App]:
        conditions = [App.status != "archived"]
        if user_id is not None:
            conditions.append(App.created_by == user_id)
        if status:
            status_list = [s.strip() for s in status.split(",")]
            conditions.append(App.status.in_(status_list))
        if search:
            conditions.append(App.name.ilike(f"%{search}%"))

        stmt = (
            select(App)
            .where(and_(*conditions))
            .order_by(App.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_app(self, app_id: int, data: dict) -> Optional[App]:
        app = await self.get_app(app_id)
        if not app:
            return None
        for key in ("name", "description", "url", "test_goal", "test_context", "icon", "color"):
            if key in data and data[key] is not None:
                setattr(app, key, data[key])
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def archive_app(self, app_id: int) -> Optional[App]:
        app = await self.get_app(app_id)
        if not app:
            return None
        app.status = "archived"
        await self.db.commit()
        return app

    async def copy_app(self, app_id: int, user_id: int) -> App:
        """Copy an existing app to create a new one for the user."""
        original = await self.get_app(app_id)
        if not original:
            raise ValueError(f"App {app_id} not found")

        # Create new conversation thread for the copy
        thread = ConversationThread(
            thread_type="planning",
            status="active",
            created_by=user_id,
            metadata={"source": "app_copy", "original_app_id": app_id},
        )
        self.db.add(thread)
        await self.db.flush()

        # Create the copy with modified metadata
        app = App(
            name=f"{original.name} (Copy)",
            description=original.description,
            url=original.url,
            test_goal=original.test_goal,
            test_context=original.test_context,
            icon=original.icon,
            color=original.color,
            status="draft",
            iteration_count=0,
            created_by=user_id,
            conversation_thread_id=thread.id,
        )
        self.db.add(app)
        await self.db.flush()

        # Add system message to the new thread
        system_msg = ConversationMessage(
            thread_id=thread.id,
            role="system",
            content=f"Copied from: {original.name}\nTarget: {app.url}\nGoal: {app.test_goal}",
            metadata={"type": "app_copied", "original_app_id": app_id, "app_id": app.id},
        )
        self.db.add(system_msg)

        # Copy test definition if exists
        if original.test_definition_id:
            original_test_def = await self.db.execute(
                select(TestDefinition).where(TestDefinition.id == original.test_definition_id)
            )
            original_test_def = original_test_def.scalar_one_or_none()

            if original_test_def:
                test_def = TestDefinition(
                    name=f"[APP] {app.name}",
                    description=app.description or app.test_goal,
                    test_id=f"app-{app.id}-{uuid.uuid4().hex[:8]}",
                    url=app.url,
                    test_goal=app.test_goal,
                    test_context=app.test_context,
                    environment={},
                    tags=["app-copied"],
                    is_active=True,
                    is_draft=True,
                    source_app_id=app.id,
                    created_by=user_id,
                )
                self.db.add(test_def)
                await self.db.flush()
                app.test_definition_id = test_def.id

        await self.db.commit()
        await self.db.refresh(app)
        return app

    # ------------------------------------------------------------------
    # Save plan version snapshot
    # ------------------------------------------------------------------

    async def _persist_steps(
        self, app: App, test_def: "TestDefinition", run_status: str = "", run_summary: str = ""
    ) -> int:
        """Create a TestVersion snapshot. Returns 1 if saved, 0 if skipped."""
        from app.models.test_version import TestVersion

        snapshot_data = {
            "name": app.name,
            "url": app.url,
            "test_goal": app.test_goal,
            "description": app.description,
            "test_context": app.test_context or {},
            "execution_mode": test_def.execution_mode,
            "script_status": test_def.script_status,
        }
        description = run_summary or "Version saved"
        version = TestVersion(
            test_definition_id=test_def.id,
            version=test_def.version,
            snapshot=snapshot_data,
            change_description=description,
            created_by="system",
        )
        self.db.add(version)
        test_def.version += 1
        await self.db.flush()
        return 1

    # ------------------------------------------------------------------
    # Step version history
    # ------------------------------------------------------------------

    async def get_step_versions(self, app_id: int) -> list:
        """Return version history for the app's test definition steps."""
        from app.models.test_version import TestVersion

        app = await self.get_app(app_id)
        if not app or not app.test_definition_id:
            return []

        result = await self.db.execute(
            select(TestVersion)
            .where(TestVersion.test_definition_id == app.test_definition_id)
            .order_by(TestVersion.version.desc())
        )
        versions = result.scalars().all()

        out = []
        for v in versions:
            desc = v.change_description or ""
            run_status = ""
            if desc.lower().startswith("passed"):
                run_status = "passed"
            elif desc.lower().startswith("failed"):
                run_status = "failed"

            out.append({
                "id": v.id,
                "version": v.version,
                "snapshot": v.snapshot,
                "change_description": desc,
                "run_status": run_status,
                "review_status": v.review_status or "draft",
                "rejection_reason": v.rejection_reason,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            })
        return out

    async def restore_step_version(self, app_id: int, version_id: int) -> dict:
        """Restore steps from a previous version snapshot."""
        from app.models.test_version import TestVersion

        app = await self.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")
        if not app.test_definition_id:
            raise ValueError("App has no test definition")

        td_stmt = select(TestDefinition).where(
            TestDefinition.id == app.test_definition_id
        )
        test_def = (await self.db.execute(td_stmt)).scalar_one_or_none()
        if not test_def:
            raise ValueError("Test definition not found")

        ver_stmt = select(TestVersion).where(
            TestVersion.id == version_id,
            TestVersion.test_definition_id == test_def.id,
        )
        version = (await self.db.execute(ver_stmt)).scalar_one_or_none()
        if not version:
            raise ValueError("Version not found")

        # Restore test definition data from snapshot
        snapshot = version.snapshot or {}
        if snapshot.get("test_goal"):
            test_def.test_goal = snapshot["test_goal"]
        if snapshot.get("url"):
            test_def.url = snapshot["url"]
        app.iteration_count += 1

        count = await self._persist_steps(
            app, test_def, run_summary=f"Restored from v{version.version}"
        )
        await self.db.commit()

        return {
            "app_id": app.id,
            "restored_from_version": version.version,
            "steps_count": count,
        }

    async def submit_version_for_review(self, app_id: int, version_id: int) -> dict:
        """Submit an existing version for admin review."""
        from app.models.test_version import TestVersion

        app = await self.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")
        if not app.test_definition_id:
            raise ValueError("App has no test definition")

        ver_stmt = select(TestVersion).where(
            TestVersion.id == version_id,
            TestVersion.test_definition_id == app.test_definition_id,
        )
        version = (await self.db.execute(ver_stmt)).scalar_one_or_none()
        if not version:
            raise ValueError("Version not found")

        if version.review_status not in ("draft", "rejected"):
            raise ValueError(f"Cannot submit version with status '{version.review_status}'")

        version.review_status = "pending_review"
        version.rejection_reason = None
        app.status = "pending_review"
        await self.db.commit()

        return {
            "app_id": app.id,
            "version_id": version.id,
            "version": version.version,
            "review_status": "pending_review",
        }

    # ------------------------------------------------------------------
    # Run — generate plan + execute
    # ------------------------------------------------------------------

    async def run_app(self, app_id: int) -> dict:
        app = await self.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")

        thread = app.conversation_thread
        if not thread:
            raise ValueError("App has no conversation thread")

        app.status = "generating"
        await self.db.flush()

        # Ensure a draft test_definition exists
        test_def = await self._ensure_draft_test_definition(app)

        # Persist version snapshot
        await self._persist_steps(app, test_def)

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

    # ------------------------------------------------------------------
    # Publish — save as persistent test definition
    # ------------------------------------------------------------------

    async def publish_app(self, app_id: int) -> dict:
        app = await self.get_app(app_id)
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
            test_def = await self._ensure_draft_test_definition(app)

        # Persist steps (this also creates a version snapshot)
        await self._persist_steps(app, test_def)

        # Create a full-config version snapshot and submit it for review
        from app.models.test_version import TestVersion
        version_snapshot = {
            "name": app.name,
            "url": app.url,
            "test_goal": app.test_goal,
            "description": app.description,
            "test_context": app.test_context or {},
            "execution_mode": test_def.execution_mode,
            "script_status": test_def.script_status,
        }
        review_version = TestVersion(
            test_definition_id=test_def.id,
            version=test_def.version,
            snapshot=version_snapshot,
            change_description="Submitted for review",
            review_status="pending_review",
            created_by="user",
        )
        self.db.add(review_version)
        test_def.version += 1

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
            "version_id": review_version.id,
            "version": review_version.version,
        }

    # ------------------------------------------------------------------
    # Sync run result into app state (called on GET app after run)
    # ------------------------------------------------------------------

    async def sync_run_result(self, app_id: int) -> Optional[App]:
        app = await self.get_app(app_id)
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
                from app.models.test_run import TestRun
                from app.models.test_case import TestCase

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
                        await self._persist_steps(app, td_row, run_status="passed", run_summary=summary)
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

        return await self.get_app(app_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
