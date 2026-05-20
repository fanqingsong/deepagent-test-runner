"""
App Service — orchestration layer for the LLM-APP-style test workspace.

Coordinates planner_agent, ExecutionService, conversation models, and
Celery tasks to provide the generate → execute → refine/publish workflow.
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
            name=data["name"],
            description=data.get("description"),
            url=data["url"],
            test_goal=data["test_goal"],
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
                )
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
            from app.agents.planner_agent import generate_test_plan

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

        # Ensure a draft test_definition exists
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

        # Dispatch Celery task
        from app.tasks.test_execution import execute_test

        task = execute_test.delay(test_def.id, run_id, app.test_context.get("environment"))

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
            "task_ids": [task.id],
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
        from app.agents.planner_agent import refine_test_plan

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
            test_def.is_draft = False
            test_def.name = app.name
            test_def.description = app.description or app.test_goal
            test_def.plan_generation_status = "approved"
        else:
            test_def = TestDefinition(
                name=app.name,
                description=app.description or app.test_goal,
                test_id=f"app-{app.id}-published",
                url=app.url,
                test_goal=app.test_goal,
                test_context=app.test_context,
                ai_generated_plan=app.current_plan,
                plan_generation_status="approved",
                environment={},
                tags=["app-published"],
                is_active=True,
                is_draft=False,
                source_app_id=app.id,
                created_by=app.created_by,
            )
            self.db.add(test_def)
            await self.db.flush()
            app.test_definition_id = test_def.id

        app.status = "published"
        await self.db.commit()
        await self.db.refresh(test_def)

        return {
            "app_id": app.id,
            "test_definition_id": test_def.id,
            "test_id": test_def.test_id,
            "name": test_def.name,
            "status": "published",
        }

    # ------------------------------------------------------------------
    # Sync run result into app state (called on GET app after run)
    # ------------------------------------------------------------------

    async def sync_run_result(self, app_id: int) -> Optional[App]:
        app = await self.get_app(app_id)
        if not app or not app.latest_run_id or app.status != "testing":
            return app

        from app.core.job_store import get_job

        job = get_job(app.latest_run_id)
        if not job or job.get("status") != "completed":
            return app

        results = job.get("results", {})
        test_runs = results.get("test_runs", [])

        thread = app.conversation_thread

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

                stmt = select(TestRun).where(TestRun.run_id == app.latest_run_id)
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

            app.latest_result = {
                "status": run_status,
                "passed": passed,
                "failed": failed,
                "total": total,
                "duration": duration,
                "run_id": app.latest_run_id,
                "steps": step_results,
            }

            if run_status == "passed" or (failed == 0 and passed > 0):
                app.status = "passed"
                if thread:
                    result_msg = ConversationMessage(
                        thread_id=thread.id,
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
                if thread:
                    result_msg = ConversationMessage(
                        thread_id=thread.id,
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

        await self.db.commit()
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
