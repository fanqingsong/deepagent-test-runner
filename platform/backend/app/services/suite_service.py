"""
Suite Service

Orchestrates test suite execution: creates suite runs, dispatches
individual test tasks (sequential or parallel), and aggregates results.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.suite_run import SuiteRun, SuiteRunEntry
from app.models.test_suite import TestSuite
from app.models.test_definition import TestDefinition

logger = logging.getLogger(__name__)


class SuiteService:
    """Service for managing suite-level test execution."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def resolve_suite_entries(self, suite: TestSuite) -> List[Dict[str, Any]]:
        """Build ordered entry list from suite_entries, dynamic rules, or fallback to test_definition_ids."""
        if suite.suite_entries:
            return [
                e for e in suite.suite_entries
                if e.get("enabled", True)
            ]

        # Fallback: generate entries from flat ID list
        return [
            {"test_definition_id": tid, "order": idx + 1, "condition": "always"}
            for idx, tid in enumerate(suite.test_definition_ids)
        ]

    async def resolve_dynamic_suite(self, suite: TestSuite) -> List[Dict[str, Any]]:
        """Resolve a dynamic suite by querying test definitions matching tag rules."""
        rule = suite.dynamic_tag_rule or {}
        match_tags = rule.get("tags", [])
        match_mode = rule.get("match", "any")

        if not match_tags:
            return []

        if match_mode == "all":
            # All tags must be present
            conditions = [
                TestDefinition.tags.any(tag) for tag in match_tags
            ]
            stmt = select(TestDefinition).where(
                *conditions,
                TestDefinition.is_draft == False,
            )
        else:
            # Any tag match
            stmt = select(TestDefinition).where(
                TestDefinition.tags.any(match_tags),
                TestDefinition.is_draft == False,
            )

        result = await self.db.execute(stmt)
        test_defs = list(result.scalars().all())

        return [
            {"test_definition_id": td.id, "order": idx + 1, "condition": "always"}
            for idx, td in enumerate(test_defs)
        ]

    async def resolve_tag_filter(self, tag_filter: str) -> List[int]:
        """Resolve a single tag filter to test definition IDs."""
        stmt = select(TestDefinition.id).where(
            TestDefinition.tags.any(tag_filter),
            TestDefinition.is_draft == False,
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def create_suite_run(
        self,
        suite_id: int,
        triggered_by: str = "manual",
        environment_overrides: Optional[Dict[str, Any]] = None,
    ) -> SuiteRun:
        """Create a SuiteRun with SuiteRunEntry rows from suite config."""
        suite = await self._get_suite(suite_id)
        if not suite:
            raise ValueError(f"Test suite {suite_id} not found")

        entries = self.resolve_suite_entries(suite)
        # Handle dynamic suites
        if not entries and suite.is_dynamic:
            entries = await self.resolve_dynamic_suite(suite)
        if not entries:
            raise ValueError(f"Test suite {suite_id} has no test entries")

        run_id = f"suite-{uuid.uuid4().hex[:12]}"
        now_ms = int(time.time() * 1000)

        # Merge environment: suite base + overrides
        merged_env = {**suite.environment_vars, **(environment_overrides or {})}

        suite_run = SuiteRun(
            suite_id=suite_id,
            run_id=run_id,
            status="pending",
            execution_mode=suite.execution_mode,
            total_tests=len(entries),
            environment=merged_env,
            triggered_by=triggered_by,
            start_time=now_ms,
        )
        self.db.add(suite_run)
        await self.db.flush()

        # Create entry rows
        entry_rows = [
            SuiteRunEntry(
                suite_run_id=suite_run.id,
                test_definition_id=e["test_definition_id"],
                entry_order=e.get("order", idx + 1),
                condition=e.get("condition", "always"),
            )
            for idx, e in enumerate(entries)
        ]
        self.db.add_all(entry_rows)
        await self.db.commit()
        await self.db.refresh(suite_run)

        logger.info(
            "Created suite run %s for suite %d with %d entries",
            run_id, suite_id, len(entry_rows)
        )
        return suite_run

    async def execute_suite(self, suite_run_id: int) -> Dict[str, Any]:
        """Orchestrate execution of a suite run."""
        suite_run = await self._get_suite_run(suite_run_id)
        if not suite_run:
            raise ValueError(f"Suite run {suite_run_id} not found")

        # Mark running
        suite_run.status = "running"
        await self.db.commit()

        # Load entries
        entries = await self._get_entries(suite_run_id)

        try:
            result = await self._execute_with_dependencies(suite_run, entries)
        except Exception as exc:
            logger.error("Suite run %d failed: %s", suite_run_id, exc)
            suite_run.status = "failed"
            suite_run.error = str(exc)
            await self.db.commit()
            raise

        # Finalize
        await self._finalize_suite_run(suite_run_id)
        return result

    async def _execute_with_dependencies(
        self, suite_run: SuiteRun, entries: List[SuiteRunEntry]
    ) -> Dict[str, Any]:
        """Execute entries respecting dependencies, conditions, and setup/teardown."""
        from app.temporal import get_temporal_client
        from app.temporal.workflows.test_execution import TestExecutionWorkflow

        suite = await self._get_suite(suite_run.suite_id)
        fail_fast = suite.fail_strategy == "fail_fast" if suite else False

        # Run setup test if defined
        if suite and suite.setup_test_id:
            await self._dispatch_single(
                suite_run, suite.setup_test_id, "setup"
            )

        # Build dependency graph from suite_entries
        suite_entries_raw = suite.suite_entries if suite else []
        dep_graph = self._build_dependency_graph(suite_entries_raw)
        layers = self._topological_sort_layers(dep_graph, entries)

        completed: Dict[int, str] = {}

        for layer in layers:
            for entry in layer:
                if not self._should_execute_entry(entry, completed):
                    entry.status = "skipped"
                    entry.finished_at = int(time.time() * 1000)
                    completed[entry.test_definition_id] = "skipped"
                    await self.db.commit()
                    continue

                if fail_fast and await self._has_failure(suite_run.id):
                    entry.status = "skipped"
                    entry.finished_at = int(time.time() * 1000)
                    completed[entry.test_definition_id] = "skipped"
                    await self.db.commit()
                    continue

                await self._execute_entry(suite_run, entry)
                # Refresh to get updated status
                await self.db.refresh(entry)
                completed[entry.test_definition_id] = entry.status

        # Run teardown test if defined
        if suite and suite.teardown_test_id:
            await self._dispatch_single(
                suite_run, suite.teardown_test_id, "teardown", execute_test
            )

        return {"run_id": suite_run.run_id, "status": "completed"}

    def _build_dependency_graph(
        self, suite_entries: List[Dict[str, Any]]
    ) -> Dict[int, List[int]]:
        """Build adjacency list: entry_id -> list of entry_ids it depends on."""
        graph: Dict[int, List[int]] = {}
        for entry in suite_entries:
            td_id = entry.get("test_definition_id")
            deps = entry.get("depends_on", [])
            if td_id is not None:
                graph[td_id] = deps
        return graph

    def _topological_sort_layers(
        self,
        dep_graph: Dict[int, List[int]],
        entries: List[SuiteRunEntry],
    ) -> List[List[SuiteRunEntry]]:
        """Sort entries into layers using Kahn's algorithm. Each layer can run in parallel."""
        entry_map = {e.test_definition_id: e for e in entries}
        all_ids = set(entry_map.keys())

        # Compute in-degree
        in_degree: Dict[int, int] = {tid: 0 for tid in all_ids}
        for tid, deps in dep_graph.items():
            if tid in in_degree:
                # Count only deps that are in our entry set
                in_degree[tid] = len([d for d in deps if d in all_ids])

        layers: List[List[SuiteRunEntry]] = []
        remaining = dict(in_degree)

        while remaining:
            # Find entries with zero in-degree
            ready = [tid for tid, deg in remaining.items() if deg == 0]
            if not ready:
                # Circular dependency — put remaining in one layer
                layer = [entry_map[tid] for tid in remaining if tid in entry_map]
                if layer:
                    layers.append(layer)
                break

            layer = [entry_map[tid] for tid in ready if tid in entry_map]
            if layer:
                layers.append(layer)

            for tid in ready:
                del remaining[tid]
                # Reduce in-degree for entries depending on this one
                for other_tid, deps in dep_graph.items():
                    if tid in deps and other_tid in remaining:
                        remaining[other_tid] = max(0, remaining[other_tid] - 1)

        return layers

    def _should_execute_entry(
        self, entry: SuiteRunEntry, completed: Dict[int, str]
    ) -> bool:
        """Check if an entry should run based on its condition and completed entries."""
        cond = entry.condition or "always"

        if cond == "always":
            return True
        elif cond == "on_success":
            return all(
                completed.get(d) in ("dispatched", "passed")
                for d in [entry.test_definition_id]
                if d in completed
            ) or not any(d in completed for d in [entry.test_definition_id])
        elif cond == "on_failure":
            return any(
                completed.get(d) in ("failed", "error")
                for d in [entry.test_definition_id]
                if d in completed
            )
        return True

    async def _dispatch_single(
        self,
        suite_run: SuiteRun,
        test_definition_id: int,
        label: str,
    ) -> None:
        """Dispatch a single setup/teardown test using Temporal workflow."""
        from app.temporal import get_temporal_client
        from app.temporal.workflows.test_execution import TestExecutionWorkflow

        now_ms = int(time.time() * 1000)
        test_run_id = f"test-{uuid.uuid4().hex[:12]}"

        try:
            client = await get_temporal_client()

            workflow_result = await client.start_workflow(
                TestExecutionWorkflow.run,
                args=[str(test_definition_id), test_run_id, suite_run.environment],
                id=f"test-execution-{test_run_id}",
                task_queue="unified-backend-task-queue",
            )

            logger.info(
                "Dispatched %s test_def=%d as run %s (workflow: %s)",
                label, test_definition_id, test_run_id, workflow_result.id
            )
        except Exception as exc:
            logger.error("Failed to dispatch %s test_def=%d: %s", label, test_definition_id, exc)

    async def _execute_entry(
        self,
        suite_run: SuiteRun,
        entry: SuiteRunEntry,
    ) -> None:
        """Execute a single entry and update its status using Temporal workflow."""
        from app.temporal import get_temporal_client
        from app.temporal.workflows.test_execution import TestExecutionWorkflow

        now_ms = int(time.time() * 1000)
        entry.status = "running"
        entry.started_at = now_ms
        await self.db.commit()

        test_run_id = f"test-{uuid.uuid4().hex[:12]}"

        try:
            client = await get_temporal_client()

            workflow_result = await client.start_workflow(
                TestExecutionWorkflow.run,
                args=[str(entry.test_definition_id), test_run_id, suite_run.environment],
                id=f"test-execution-{test_run_id}",
                task_queue="unified-backend-task-queue",
            )

            entry.test_run_id = test_run_id
            entry.status = "dispatched"
            logger.info(
                "Dispatched entry %d (test_def=%d) as run %s (workflow: %s)",
                entry.entry_order, entry.test_definition_id, test_run_id, workflow_result.id
            )
        except Exception as exc:
            entry.status = "error"
            entry.error_message = str(exc)
            logger.error(
                "Failed to dispatch entry %d: %s", entry.entry_order, exc
            )

        entry.finished_at = int(time.time() * 1000)
        entry.duration = entry.finished_at - now_ms
        await self.db.commit()

    async def _finalize_suite_run(self, suite_run_id: int) -> SuiteRun:
        """Aggregate entry statuses into suite run totals."""
        suite_run = await self._get_suite_run(suite_run_id)
        entries = await self._get_entries(suite_run_id)

        # Poll dispatched entries for their test_run status
        passed = failed = skipped = 0
        for entry in entries:
            if entry.status in ("passed",):
                passed += 1
            elif entry.status in ("failed", "error"):
                failed += 1
            elif entry.status in ("skipped",):
                skipped += 1
            else:
                # Still dispatched/pending/running — count as pending
                pass

        suite_run.passed = passed
        suite_run.failed = failed
        suite_run.skipped = skipped
        suite_run.end_time = int(time.time() * 1000)
        if suite_run.start_time and suite_run.end_time:
            suite_run.total_duration = suite_run.end_time - suite_run.start_time

        # Determine overall status
        if failed > 0:
            suite_run.status = "failed"
        elif skipped > 0 and passed == suite_run.total_tests - skipped:
            suite_run.status = "passed"
        elif passed == suite_run.total_tests:
            suite_run.status = "passed"
        else:
            suite_run.status = "partial"

        await self.db.commit()
        await self.db.refresh(suite_run)
        logger.info(
            "Finalized suite run %s: status=%s passed=%d failed=%d skipped=%d",
            suite_run.run_id, suite_run.status, passed, failed, skipped
        )
        return suite_run

    async def cancel_suite_run(self, suite_run_id: int) -> SuiteRun:
        """Cancel a running suite run, marking remaining entries as skipped."""
        suite_run = await self._get_suite_run(suite_run_id)
        if not suite_run:
            raise ValueError(f"Suite run {suite_run_id} not found")
        if suite_run.status not in ("pending", "running"):
            raise ValueError(f"Cannot cancel suite run in status {suite_run.status}")

        entries = await self._get_entries(suite_run_id)
        now_ms = int(time.time() * 1000)
        for entry in entries:
            if entry.status in ("pending", "dispatched"):
                entry.status = "skipped"
                entry.finished_at = now_ms

        suite_run.status = "cancelled"
        suite_run.end_time = now_ms
        await self.db.commit()
        await self.db.refresh(suite_run)
        return suite_run

    async def list_suite_runs(
        self, suite_id: int, skip: int = 0, limit: int = 50
    ) -> List[SuiteRun]:
        """List runs for a suite, newest first."""
        result = await self.db.execute(
            select(SuiteRun)
            .where(SuiteRun.suite_id == suite_id)
            .order_by(SuiteRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_suite_run_with_entries(self, run_id: str) -> Optional[SuiteRun]:
        """Get a suite run by run_id with all entries loaded."""
        result = await self.db.execute(
            select(SuiteRun)
            .where(SuiteRun.run_id == run_id)
            .options(selectinload(SuiteRun.entries))
        )
        return result.unique().scalar_one_or_none()

    # --- Private helpers ---

    async def _get_suite(self, suite_id: int) -> Optional[TestSuite]:
        result = await self.db.execute(
            select(TestSuite).where(TestSuite.id == suite_id)
        )
        return result.scalar_one_or_none()

    async def _get_suite_run(self, suite_run_id: int) -> Optional[SuiteRun]:
        result = await self.db.execute(
            select(SuiteRun).where(SuiteRun.id == suite_run_id)
        )
        return result.scalar_one_or_none()

    async def _get_entries(self, suite_run_id: int) -> List[SuiteRunEntry]:
        result = await self.db.execute(
            select(SuiteRunEntry)
            .where(SuiteRunEntry.suite_run_id == suite_run_id)
            .order_by(SuiteRunEntry.entry_order)
        )
        return list(result.scalars().all())

    async def _has_failure(self, suite_run_id: int) -> bool:
        result = await self.db.execute(
            select(SuiteRunEntry)
            .where(
                SuiteRunEntry.suite_run_id == suite_run_id,
                SuiteRunEntry.status.in_(["failed", "error"])
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _skip_remaining(self, suite_run_id: int, from_order: int) -> None:
        entries = await self._get_entries(suite_run_id)
        now_ms = int(time.time() * 1000)
        for entry in entries:
            if entry.entry_order >= from_order and entry.status in ("pending",):
                entry.status = "skipped"
                entry.finished_at = now_ms
        await self.db.commit()

    async def _get_fail_strategy(self, suite_id: int) -> bool:
        suite = await self._get_suite(suite_id)
        return suite.fail_strategy == "fail_fast" if suite else False
