"""
App Service — orchestration layer for the LLM-APP-style test workspace.

Coordinates planner_agent, ExecutionService, conversation models, and
Temporal workflows to provide the generate → execute → refine/publish workflow.
"""

import json
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

    async def _ensure_draft_test_definition(self, app: App, plan: dict) -> "TestDefinition":
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
                ai_generated_plan=plan,
                plan_generation_status="generated",
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
            test_def.ai_generated_plan = plan
            test_def.plan_generation_status = "generated"
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
        user_id: int,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[App]:
        conditions = [App.created_by == user_id, App.status != "archived"]
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
        for key in ("name", "description", "url", "test_goal", "test_context", "icon", "color", "current_plan"):
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
            current_plan=original.current_plan,
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
                    ai_generated_plan=app.current_plan,
                    plan_generation_status="generated" if app.current_plan else "pending",
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
    # Generate plan only (no execution)
    # ------------------------------------------------------------------

    async def generate_plan_only(self, app_id: int) -> dict:
        app = await self.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")

        thread = app.conversation_thread
        if not thread:
            raise ValueError("App has no conversation thread")

        app.status = "generating"
        await self.db.flush()

        from app.agents.test_runner.planner_agent import generate_test_plan

        plan = await generate_test_plan(
            goal=app.test_goal,
            url=app.url,
            context=app.test_context,
        )
        app.current_plan = plan

        await self._ensure_draft_test_definition(app, plan)

        plan_text = self._format_plan_text(plan)
        ai_msg = ConversationMessage(
            thread_id=thread.id,
            role="assistant",
            content=plan_text,
            metadata={"type": "plan_generated", "plan": plan},
        )
        self.db.add(ai_msg)

        app.status = "draft"
        await self.db.commit()

        return {"app_id": app.id, "plan": plan, "status": "draft"}

    # ------------------------------------------------------------------
    # Save steps to test_steps table
    # ------------------------------------------------------------------

    async def _persist_steps(
        self, app: App, test_def: "TestDefinition", run_status: str = "", run_summary: str = ""
    ) -> int:
        """Write current_plan steps into test_steps rows. Returns count saved.

        Before overwriting, creates a TestVersion snapshot of existing steps.
        """
        from app.models.test_step import TestStep
        from app.models.test_version import TestVersion
        from sqlalchemy import delete as sa_delete

        plan = app.current_plan or {}
        steps = plan.get("steps", [])
        if not steps:
            return 0

        # Snapshot existing steps before overwriting
        existing = await self.db.execute(
            select(TestStep)
            .where(TestStep.test_definition_id == test_def.id)
            .order_by(TestStep.step_number)
        )
        existing_steps = existing.scalars().all()

        if existing_steps:
            snapshot_data = {
                "name": app.name,
                "url": app.url,
                "test_goal": app.test_goal,
                "description": app.description,
                "test_context": app.test_context or {},
                "steps": [
                    {
                        "step_number": s.step_number,
                        "description": s.description,
                        "type": s.type,
                        "params": s.params,
                        "expected_result": s.expected_result,
                    }
                    for s in existing_steps
                ]
            }
            description = run_summary or "Saved before overwrite"
            version = TestVersion(
                test_definition_id=test_def.id,
                version=test_def.version,
                snapshot=snapshot_data,
                change_description=description,
                created_by="system",
            )
            self.db.add(version)
            test_def.version += 1

        await self.db.execute(
            sa_delete(TestStep).where(
                TestStep.test_definition_id == test_def.id
            )
        )
        new_steps = [
            TestStep(
                test_definition_id=test_def.id,
                step_number=s.get("step_number", idx + 1),
                description=s.get("description", ""),
                type=s.get("type", "action"),
                params=s.get("params", {}),
                expected_result=s.get("verification") or s.get("expected_result"),
                is_ai_generated=True,
                confidence_score=s.get("confidence"),
            )
            for idx, s in enumerate(steps)
        ]
        self.db.add_all(new_steps)
        await self.db.flush()
        return len(new_steps)

    async def save_steps_to_db(self, app_id: int) -> dict:
        app = await self.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")

        plan = app.current_plan or {}
        steps = plan.get("steps", [])
        if not steps:
            raise ValueError("No steps to save — generate a plan first")

        test_def = await self._ensure_draft_test_definition(app, plan)
        count = await self._persist_steps(app, test_def)
        await self.db.commit()

        return {
            "app_id": app.id,
            "test_definition_id": test_def.id,
            "steps_count": count,
            "status": "saved",
        }

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

        # Update current_plan with snapshot steps
        snapshot_steps = (version.snapshot or {}).get("steps", [])
        current_plan = app.current_plan or {}
        current_plan["steps"] = snapshot_steps
        app.current_plan = current_plan
        app.iteration_count += 1

        # Persist (will auto-create version snapshot of current steps before overwriting)
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

    async def run_app(self, app_id: int, force_regenerate: bool = False, use_existing_plan: bool = False) -> dict:
        app = await self.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")

        thread = app.conversation_thread
        if not thread:
            raise ValueError("App has no conversation thread")

        app.status = "generating"
        await self.db.flush()

        # Generate plan if needed
        plan = app.current_plan
        if not use_existing_plan and (force_regenerate or not plan or not plan.get("steps")):
            from app.agents.test_runner.planner_agent import generate_test_plan

            plan = await generate_test_plan(
                goal=app.test_goal,
                url=app.url,
                context=app.test_context,
            )
            app.current_plan = plan

            plan_text = self._format_plan_text(plan)
            ai_msg = ConversationMessage(
                thread_id=thread.id,
                role="assistant",
                content=plan_text,
                metadata={"type": "plan_generated", "plan": plan},
            )
            self.db.add(ai_msg)

        # Ensure a draft test_definition exists and plan is synced
        test_def = await self._ensure_draft_test_definition(app, plan)

        # Persist steps to test_steps table so executor can access them
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
        from app.workflows.test_execution import TestExecutionWorkflow

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
            "total_steps": len(plan.get("steps", [])),
            "completed_steps": [],
            "current_step": 0,
        })

        app.status = "testing"
        app.latest_run_id = run_id
        app.iteration_count += 1
        await self.db.commit()

        return {"job_id": run_id, "run_id": run_id, "status": "running"}

    # ------------------------------------------------------------------
    # Refine — user feedback → re-plan
    # ------------------------------------------------------------------

    async def refine_app(self, app_id: int, feedback: str) -> dict:
        app = await self.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")

        thread = app.conversation_thread
        if not thread:
            raise ValueError("App has no conversation thread")

        # Add user message
        user_msg = ConversationMessage(
            thread_id=thread.id,
            role="user",
            content=feedback,
            metadata={"type": "refine_feedback"},
        )
        self.db.add(user_msg)
        await self.db.flush()

        # Build conversation history for planner
        history = [
            {"role": m.role, "content": m.content}
            for m in thread.messages
        ]

        # Refine plan
        from app.agents.test_runner.planner_agent import refine_test_plan

        refined = await refine_test_plan(
            goal=app.test_goal,
            url=app.url,
            current_plan=app.current_plan,
            conversation_history=history,
            user_feedback=feedback,
            context=app.test_context,
        )
        app.current_plan = refined

        plan_text = self._format_plan_text(refined)
        ai_msg = ConversationMessage(
            thread_id=thread.id,
            role="assistant",
            content=plan_text,
            metadata={"type": "plan_refined", "plan": refined},
        )
        self.db.add(ai_msg)

        app.status = "draft"
        await self.db.commit()

        return {"status": "refined", "plan": refined}

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
            test_def = await self._ensure_draft_test_definition(app, app.current_plan or {})

        # Persist steps (this also creates a version snapshot)
        await self._persist_steps(app, test_def)

        # Create a full-config version snapshot and submit it for review
        from app.models.test_version import TestVersion
        steps = (app.current_plan or {}).get("steps", [])
        version_snapshot = {
            "name": app.name,
            "url": app.url,
            "test_goal": app.test_goal,
            "description": app.description,
            "test_context": app.test_context or {},
            "steps": steps,
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

    @staticmethod
    def _format_plan_text(plan: dict) -> str:
        steps = plan.get("steps", [])
        lines = ["Generated test plan:\n"]
        for step in steps:
            num = step.get("step_number", "?")
            desc = step.get("description", "")
            vtype = step.get("type", "")
            verification = step.get("verification", "")
            lines.append(f"Step {num}: [{vtype}] {desc}")
            if verification:
                lines.append(f"  Verify: {verification}")
        lines.append(f"\nEstimated duration: {plan.get('estimated_duration', '?')}s")
        return "\n".join(lines)
