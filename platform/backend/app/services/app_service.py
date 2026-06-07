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

from app.models.test_workspace import TestWorkspace
from app.models.conversation import ConversationMessage, ConversationThread
from app.models.test_definition import TestDefinition

logger = logging.getLogger(__name__)


class AppService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    async def _ensure_draft_test_definition(self, workspace: TestWorkspace) -> "TestDefinition":
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

    async def create_app(self, user_id: int, data: dict) -> TestWorkspace:
        thread = ConversationThread(
            thread_type="planning",
            status="active",
            created_by=user_id,
            metadata={"source": "app_workspace"},
        )
        self.db.add(thread)
        await self.db.flush()

        app = TestWorkspace(
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

    async def get_app(self, workspace_id: int) -> Optional[TestWorkspace]:
        stmt = (
            select(TestWorkspace)
            .options(
                selectinload(TestWorkspace.conversation_thread).selectinload(
                    ConversationThread.messages
                ),
                selectinload(TestWorkspace.test_definition),
            )
            .where(TestWorkspace.id == workspace_id)
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
    ) -> List[dict]:
        conditions = [TestWorkspace.status != "archived"]
        if user_id is not None:
            conditions.append(TestWorkspace.created_by == user_id)
        if status:
            status_list = [s.strip() for s in status.split(",")]
            conditions.append(TestWorkspace.status.in_(status_list))
        if search:
            conditions.append(TestWorkspace.name.ilike(f"%{search}%"))

        stmt = (
            select(TestWorkspace)
            .where(and_(*conditions))
            .order_by(TestWorkspace.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        workspaces = list(result.scalars().all())

        # For published items, fetch the latest published version number
        output = []
        for workspace in workspaces:
            workspace_dict = {
                "id": workspace.id,
                "name": workspace.name,
                "description": workspace.description,
                "url": workspace.url,
                "status": workspace.status,
                "test_goal": workspace.test_goal,
                "icon": workspace.icon,
                "color": workspace.color,
                "iteration_count": workspace.iteration_count,
                "latest_result": workspace.latest_result or {},
                "created_at": workspace.created_at,
                "updated_at": workspace.updated_at,
            }

            # If this is a published marketplace item, get the latest published version
            if workspace.status == "published" and workspace.test_definition_id:
                from app.models.test_version import TestVersion
                ver_stmt = (
                    select(TestVersion)
                    .where(
                        TestVersion.test_definition_id == workspace.test_definition_id,
                        TestVersion.review_status == "published",
                    )
                    .order_by(TestVersion.version.desc())
                    .limit(1)
                )
                ver_result = await self.db.execute(ver_stmt)
                published_version = ver_result.scalar_one_or_none()
                if published_version:
                    workspace_dict["iteration_count"] = published_version.version

            output.append(workspace_dict)

        return output

    async def update_app(self, workspace_id: int, data: dict) -> Optional[TestWorkspace]:
        app = await self.get_app(workspace_id)
        if not app:
            return None
        for key in ("name", "description", "url", "test_goal", "test_context", "icon", "color"):
            if key in data and data[key] is not None:
                setattr(app, key, data[key])

        # Sync config changes to the draft version snapshot
        if app.test_definition_id:
            from app.models.test_version import TestVersion
            stmt = (
                select(TestVersion)
                .where(
                    TestVersion.test_definition_id == app.test_definition_id,
                    TestVersion.review_status == "draft",
                )
                .order_by(TestVersion.id.desc())
                .limit(1)
            )
            result = await self.db.execute(stmt)
            draft_version = result.scalar_one_or_none()
            if draft_version:
                td_stmt = select(TestDefinition).where(
                    TestDefinition.id == app.test_definition_id
                )
                td_result = await self.db.execute(td_stmt)
                test_def = td_result.scalar_one_or_none()
                if test_def:
                    draft_version.snapshot = await self._build_snapshot(app, test_def)

        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def archive_app(self, workspace_id: int) -> Optional[TestWorkspace]:
        app = await self.get_app(workspace_id)
        if not app:
            return None
        app.status = "archived"
        await self.db.commit()
        return app

    async def copy_app(self, workspace_id: int, user_id: int) -> TestWorkspace:
        """Copy an existing app to create a new one for the user."""
        original = await self.get_app(workspace_id)
        if not original:
            raise ValueError(f"App {workspace_id} not found")

        # Create new conversation thread for the copy
        thread = ConversationThread(
            thread_type="planning",
            status="active",
            created_by=user_id,
            metadata={"source": "app_copy", "original_app_id": workspace_id},
        )
        self.db.add(thread)
        await self.db.flush()

        # Create the copy with modified metadata
        app = TestWorkspace(
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
            metadata={"type": "app_copied", "original_app_id": workspace_id, "app_id": app.id},
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
    # Version snapshot helpers
    # ------------------------------------------------------------------

    async def _build_snapshot(self, app: TestWorkspace, test_def: "TestDefinition") -> dict:
        """Build snapshot for version storage, including permissions."""
        from app.models.test_workspace_permission import TestWorkspacePermission
        from app.models.user import User

        # Load current permissions for this workspace
        stmt = select(TestWorkspacePermission, User).join(
            User, TestWorkspacePermission.user_id == User.id
        ).where(TestWorkspacePermission.workspace_id == app.id)
        result = await self.db.execute(stmt)
        permissions = [
            {
                "user_id": perm.user_id,
                "username": user.username,
                "email": user.email,
                "permission_type": perm.permission_type,
            }
            for perm, user in result.all()
        ]

        return {
            "name": app.name,
            "url": app.url,
            "test_goal": app.test_goal,
            "description": app.description,
            "test_context": app.test_context or {},
            "execution_mode": test_def.execution_mode,
            "script_status": test_def.script_status,
            "playwright_script": test_def.playwright_script,
            "script_metadata": test_def.script_metadata or {},
            "permissions": permissions,
        }

    async def _apply_permissions_to_workspace(
        self, workspace_id: int, permissions: list
    ) -> None:
        """Apply permissions from snapshot to workspace permissions table."""
        from app.models.test_workspace_permission import TestWorkspacePermission

        # Clear existing permissions
        stmt = select(TestWorkspacePermission).where(
            TestWorkspacePermission.workspace_id == workspace_id
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().all()
        for perm in existing:
            await self.db.delete(perm)

        # Apply new permissions from snapshot
        for perm_data in permissions:
            perm = TestWorkspacePermission(
                workspace_id=workspace_id,
                user_id=perm_data["user_id"],
                permission_type=perm_data["permission_type"],
                granted_by=None,  # From version restore
            )
            self.db.add(perm)

        await self.db.flush()

    async def _get_or_create_draft_version(
        self, workspace: TestWorkspace, test_def: "TestDefinition"
    ) -> "TestVersion":
        """Return the single active draft TestVersion, creating one if needed."""
        from app.models.test_version import TestVersion

        stmt = (
            select(TestVersion)
            .where(
                TestVersion.test_definition_id == test_def.id,
                TestVersion.review_status == "draft",
            )
            .order_by(TestVersion.id.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        draft = TestVersion(
            test_definition_id=test_def.id,
            version=0,  # Will be assigned next version number on submit
            snapshot=await self._build_snapshot(app, test_def),
            change_description="Initial draft",
            review_status="draft",
            created_by="system",
        )
        self.db.add(draft)
        await self.db.flush()
        return draft

    # ------------------------------------------------------------------
    # Save plan version snapshot (in-place update for draft)
    # ------------------------------------------------------------------

    async def _persist_steps(
        self, workspace: TestWorkspace, test_def: "TestDefinition", run_status: str = "", run_summary: str = ""
    ) -> int:
        """Update the existing draft version's snapshot in-place."""
        draft_version = await self._get_or_create_draft_version(workspace, test_def)
        draft_version.snapshot = await self._build_snapshot(workspace, test_def)
        draft_version.change_description = run_summary or "Draft updated"
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

    async def get_published_versions(self, app_id: int) -> list:
        """Return all approved/published versions for marketplace browsing."""
        from app.models.test_version import TestVersion

        app = await self.get_app(app_id)
        if not app or not app.test_definition_id:
            return []

        result = await self.db.execute(
            select(TestVersion)
            .where(
                TestVersion.test_definition_id == app.test_definition_id,
                TestVersion.review_status.in_(["approved", "published"]),
            )
            .order_by(TestVersion.version.desc())
        )
        versions = result.scalars().all()
        return [
            {
                "id": v.id,
                "version": v.version,
                "snapshot": v.snapshot,
                "change_description": v.change_description,
                "review_status": v.review_status,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

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
        if snapshot.get("playwright_script"):
            test_def.playwright_script = snapshot["playwright_script"]
        if snapshot.get("script_metadata"):
            test_def.script_metadata = snapshot["script_metadata"]
        app.iteration_count += 1

        # Apply permissions from snapshot
        if "permissions" in snapshot:
            await self._apply_permissions_to_workspace(
                app.id, snapshot["permissions"]
            )

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

        # Lock in version number on submit
        td_stmt = select(TestDefinition).where(
            TestDefinition.id == app.test_definition_id
        )
        test_def = (await self.db.execute(td_stmt)).scalar_one_or_none()
        if test_def and version.version == 0:
            # Legacy support: if draft still uses version=0, assign now
            test_def.version += 1
            version.version = test_def.version
        elif test_def and version.version > test_def.version:
            # Draft already has a version number, update test_definition.version to match
            test_def.version = version.version

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
        """Submit the current draft version for admin review."""
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

        # Get or create the draft version, update snapshot one final time
        draft_version = await self._get_or_create_draft_version(app, test_def)
        draft_version.snapshot = await self._build_snapshot(app, test_def)
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

    # ------------------------------------------------------------------
    # Sync run result into app state (called on GET app after run)
    # ------------------------------------------------------------------

    async def sync_run_result(self, app_id: int) -> Optional[TestWorkspace]:
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
