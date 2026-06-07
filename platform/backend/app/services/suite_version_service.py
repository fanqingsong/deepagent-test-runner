"""
Suite Version Service — manages test suite version lifecycle.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_suite import TestSuite
from app.models.test_suite_version import TestSuiteVersion
from app.models.user import User


class SuiteVersionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_versions(self, test_suite_id: int) -> list[TestSuiteVersion]:
        """List all versions of a test suite, newest first."""
        result = await self.db.execute(
            select(TestSuiteVersion)
            .where(TestSuiteVersion.test_suite_id == test_suite_id)
            .order_by(TestSuiteVersion.version.desc(), TestSuiteVersion.id.desc())
        )
        return list(result.scalars().all())

    async def create_version(
        self,
        test_suite_id: int,
        snapshot: dict,
        change_description: Optional[str] = None,
        created_by: str = "system",
    ) -> TestSuiteVersion:
        """Create a new version for a test suite."""
        # Get next version number (only for non-draft versions)
        result = await self.db.execute(
            select(TestSuiteVersion.version)
            .where(TestSuiteVersion.test_suite_id == test_suite_id)
            .order_by(TestSuiteVersion.version.desc())
            .limit(1)
        )
        max_version = result.scalar_one_or_none()
        next_version = (max_version or 0) + 1

        version = TestSuiteVersion(
            test_suite_id=test_suite_id,
            version=next_version,
            snapshot=snapshot,
            change_description=change_description,
            review_status="draft",
            created_by=created_by,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def restore_version(
        self,
        test_suite_id: int,
        version_id: int,
    ) -> TestSuite:
        """Restore a test suite to a specific version."""
        # Get test suite
        result = await self.db.execute(
            select(TestSuite).where(TestSuite.id == test_suite_id)
        )
        suite = result.scalar_one_or_none()
        if not suite:
            raise ValueError(f"Test suite {test_suite_id} not found")

        # Get version
        result = await self.db.execute(
            select(TestSuiteVersion).where(TestSuiteVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        if not version or version.test_suite_id != test_suite_id:
            raise ValueError(f"Version {version_id} not found for suite {test_suite_id}")

        # Restore from snapshot
        snapshot = version.snapshot
        suite.name = snapshot.get("name", suite.name)
        suite.description = snapshot.get("description")
        suite.execution_mode = snapshot.get("execution_mode", "sequential")
        suite.max_concurrency = snapshot.get("max_concurrency", 1)
        suite.fail_strategy = snapshot.get("fail_strategy", "continue")
        suite.retry_config = snapshot.get("retry_config", {})
        suite.environment_vars = snapshot.get("environment_vars", {})
        suite.suite_entries = snapshot.get("suite_entries", [])
        suite.test_definition_ids = snapshot.get("test_definition_ids", [])
        suite.is_dynamic = snapshot.get("is_dynamic", False)
        suite.dynamic_tag_rule = snapshot.get("dynamic_tag_rule", {})
        suite.setup_test_id = snapshot.get("setup_test_id")
        suite.teardown_test_id = snapshot.get("teardown_test_id")
        suite.schedule_enabled = snapshot.get("schedule_enabled", False)
        suite.cron_expression = snapshot.get("cron_expression")
        suite.timezone = snapshot.get("timezone", "Asia/Shanghai")
        suite.schedule_allow_concurrent = snapshot.get("schedule_allow_concurrent", False)
        suite.schedule_max_retries = snapshot.get("schedule_max_retries", 0)
        suite.schedule_retry_interval = snapshot.get("schedule_retry_interval", 60)

        # Create a new draft version for the restored state
        await self.create_version(
            test_suite_id,
            self._suite_to_dict(suite),
            f"Restored from v{version.version}",
            "system",
        )

        await self.db.commit()
        await self.db.refresh(suite)
        return suite

    async def submit_for_review(
        self,
        test_suite_id: int,
        version_id: int,
    ) -> TestSuiteVersion:
        """Submit a version for review."""
        result = await self.db.execute(
            select(TestSuiteVersion).where(TestSuiteVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        if not version or version.test_suite_id != test_suite_id:
            raise ValueError("Version not found")

        if version.review_status not in ("draft", "rejected"):
            raise ValueError(f"Cannot submit version with status {version.review_status}")

        # Assign version number if it's a draft (version 0)
        if version.version == 0:
            result = await self.db.execute(
                select(TestSuiteVersion.version)
                .where(TestSuiteVersion.test_suite_id == test_suite_id)
                .order_by(TestSuiteVersion.version.desc())
                .limit(1)
            )
            max_version = result.scalar_one_or_none()
            version.version = (max_version or 0) + 1

        version.review_status = "pending_review"
        version.rejection_reason = None
        await self.db.commit()
        await self.db.refresh(version)
        return version

    def _suite_to_dict(self, suite: TestSuite) -> dict:
        """Convert TestSuite model to dict for snapshot storage."""
        return {
            "name": suite.name,
            "description": suite.description,
            "execution_mode": suite.execution_mode,
            "max_concurrency": suite.max_concurrency,
            "fail_strategy": suite.fail_strategy,
            "retry_config": suite.retry_config,
            "environment_vars": suite.environment_vars,
            "suite_entries": suite.suite_entries,
            "test_definition_ids": suite.test_definition_ids,
            "is_dynamic": suite.is_dynamic,
            "dynamic_tag_rule": suite.dynamic_tag_rule,
            "setup_test_id": suite.setup_test_id,
            "teardown_test_id": suite.teardown_test_id,
            "schedule_enabled": suite.schedule_enabled,
            "cron_expression": suite.cron_expression,
            "timezone": suite.timezone,
            "schedule_allow_concurrent": suite.schedule_allow_concurrent,
            "schedule_max_retries": suite.schedule_max_retries,
            "schedule_retry_interval": suite.schedule_retry_interval,
        }
