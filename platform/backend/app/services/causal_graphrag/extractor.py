"""
Data extractor.

Reads the existing relational tables (test_runs / test_cases /
test_definitions) and produces a tidy, per-test-case pandas DataFrame enriched
with normalized error categories and selectors. This DataFrame is the single
source of truth for both graph building and causal inference.

No relational schema changes are made - this is a read-only extractor.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.causal_graphrag.error_normalizer import normalize

logger = logging.getLogger(__name__)

# Optional per-case overrides embedded in the test case description, e.g.
# "[env=production] [browser=firefox]". Real runs keep environment on the
# definition; this convention lets a single definition carry per-case
# environment/browser metadata (useful for environment causal analysis).
_ENV_OVERRIDE_RE = re.compile(r"\[env=([\w\-.]+)\]", re.IGNORECASE)
_BROWSER_OVERRIDE_RE = re.compile(r"\[browser=([\w\-.]+)\]", re.IGNORECASE)


# One row per test_case result, joined with its run and definition.
_EXTRACT_SQL = text(
    """
    SELECT
        tc.id                AS case_id,
        tc.test_id           AS case_test_id,
        tc.description        AS case_description,
        tc.status            AS case_status,
        tc.duration          AS case_duration,
        tc.error_message     AS case_error_message,
        tc.screenshot_path   AS screenshot_path,
        tc.created_at        AS case_created_at,
        tr.id                AS run_pk,
        tr.run_id            AS run_id,
        tr.status            AS run_status,
        tr.error_message     AS run_error_message,
        tr.created_at        AS run_created_at,
        td.id                AS def_id,
        td.name              AS def_name,
        td.test_id           AS def_test_id,
        td.url               AS def_url,
        td.version           AS def_version,
        td.updated_at        AS def_updated_at,
        td.environment       AS def_environment,
        td.tags              AS def_tags
    FROM test_cases tc
    LEFT JOIN test_runs tr ON tc.run_id = tr.id
    LEFT JOIN test_definitions td
        ON COALESCE(tc.test_definition_id, tr.test_definition_id) = td.id
    WHERE (CAST(:since AS timestamp) IS NULL OR tc.created_at >= CAST(:since AS timestamp))
    ORDER BY tc.created_at ASC
    """
)


def _env_name(environment: Any) -> str:
    """Best-effort extraction of an environment name from the JSONB column."""
    if not environment:
        return "default"
    if isinstance(environment, str):
        return environment or "default"
    if isinstance(environment, dict):
        for key in ("name", "env", "environment", "stage", "target"):
            val = environment.get(key)
            if val:
                return str(val)
        return "default"
    return "default"


def _browser_name(environment: Any) -> str:
    """Best-effort extraction of the browser from the JSONB column."""
    if isinstance(environment, dict):
        for key in ("browser", "browser_name", "browserName"):
            val = environment.get(key)
            if val:
                return str(val)
    return "chromium"


def _apply_override(description: Optional[str], regex: re.Pattern, default: str) -> str:
    """Return an override value parsed from the description, or the default."""
    if description:
        match = regex.search(description)
        if match:
            return match.group(1)
    return default


class DataExtractor:
    """Builds the per-test-case analysis DataFrame from PostgreSQL."""

    async def extract(
        self,
        db: AsyncSession,
        days: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Extract and enrich test execution data.

        Args:
            db: Async SQLAlchemy session.
            days: If provided, only include cases created in the last N days.

        Returns:
            A pandas DataFrame, one row per test case result, with normalized
            error metadata. May be empty if there is no data.
        """
        since = None
        if days is not None:
            since = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(_EXTRACT_SQL, {"since": since})
        rows = result.mappings().all()

        if not rows:
            logger.info("DataExtractor: no rows found (days=%s)", days)
            return pd.DataFrame()

        records: list[Dict[str, Any]] = []
        for r in rows:
            status = (r["case_status"] or "").lower()
            passed = status in ("passed", "pass", "success", "ok")
            error_message = r["case_error_message"] or r["run_error_message"]
            category, signature, selectors = normalize(error_message)
            environment = r["def_environment"]
            description = r["case_description"]
            env_name = _apply_override(description, _ENV_OVERRIDE_RE, _env_name(environment))
            browser_name = _apply_override(description, _BROWSER_OVERRIDE_RE, _browser_name(environment))

            records.append(
                {
                    "case_id": r["case_id"],
                    "case_test_id": r["case_test_id"],
                    "status": status,
                    "passed": int(passed),
                    "failed": int(not passed),
                    "duration": int(r["case_duration"] or 0),
                    "error_message": error_message,
                    "error_category": category if not passed else "None",
                    "error_signature": signature if not passed else "None",
                    "selectors": selectors if not passed else [],
                    "screenshot_path": r["screenshot_path"],
                    "case_created_at": r["case_created_at"],
                    "run_pk": r["run_pk"],
                    "run_id": r["run_id"] or f"run-{r['run_pk']}",
                    "run_status": r["run_status"],
                    "run_created_at": r["run_created_at"],
                    "def_id": r["def_id"],
                    "def_name": r["def_name"] or (f"definition-{r['def_id']}" if r["def_id"] else "unknown"),
                    "def_url": r["def_url"] or "",
                    "def_version": int(r["def_version"] or 1),
                    "def_updated_at": r["def_updated_at"],
                    "environment": env_name,
                    "browser": browser_name,
                    "tags": list(r["def_tags"] or []),
                }
            )

        df = pd.DataFrame.from_records(records)
        logger.info(
            "DataExtractor: extracted %d test case rows across %d runs",
            len(df),
            df["run_id"].nunique() if not df.empty else 0,
        )
        return df
