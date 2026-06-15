"""
Seed demo data for Causal GraphRAG root cause analysis.

Creates three clearly distinguishable scenarios so the demo shows all three
causal verdicts:

1. Regression: a login test that passes for the first ~25 days, then a "deploy"
   introduces a Timeout failure on #login-btn -> pass rate collapses.
2. Flaky: a search test that randomly passes/fails (~50%) in the same
   environment and version -> no deterministic cause.
3. Environment issue: a checkout test that passes on chromium but fails on
   firefox (encoded per-case via the description marker [browser=...]).

Run inside the backend container:
    docker compose exec backend python -m scripts.seed_root_cause_demo
or locally with the backend venv and DATABASE_URL set.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta

from sqlalchemy import delete, text

from app.core.database import async_session_maker
from app.models.test_case import TestCase
from app.models.test_definition import TestDefinition
from app.models.test_run import TestRun

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_root_cause_demo")

random.seed(42)

# Stable test_id prefixes so re-running cleans up previous demo data.
REG_TID = "rc-demo-regression"
FLAKY_TID = "rc-demo-flaky"
ENV_TID = "rc-demo-env"

TIMEOUT_ERR = (
    'TimeoutError: page.click: Timeout 30000ms exceeded.\n'
    'waiting for selector "#login-btn"'
)
SELECTOR_ERR = (
    'Error: locator(".search-result") resolved to 0 elements. '
    "no element found"
)
FIREFOX_ERR = (
    'Error: expect(locator).toBeVisible() failed. '
    'waiting for selector ".checkout-summary" — element is not visible'
)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


async def _cleanup(session):
    """Remove any previously seeded demo definitions, runs and cases."""
    defs = (await session.execute(
        TestDefinition.__table__.select().where(
            TestDefinition.test_id.in_([REG_TID, FLAKY_TID, ENV_TID])
        )
    )).fetchall()
    def_ids = [row.id for row in defs]
    run_ids_prefixes = [REG_TID, FLAKY_TID, ENV_TID]

    if def_ids:
        await session.execute(delete(TestCase).where(TestCase.test_definition_id.in_(def_ids)))
    # Runs and cases are keyed by run_id prefixes too.
    for prefix in run_ids_prefixes:
        runs = (await session.execute(
            TestRun.__table__.select().where(TestRun.run_id.like(f"{prefix}-%"))
        )).fetchall()
        rids = [r.id for r in runs]
        if rids:
            await session.execute(delete(TestCase).where(TestCase.run_id.in_(rids)))
        await session.execute(delete(TestRun).where(TestRun.run_id.like(f"{prefix}-%")))
    if def_ids:
        await session.execute(delete(TestDefinition).where(TestDefinition.id.in_(def_ids)))
    await session.flush()


async def _make_definition(session, name, test_id, url, environment, description) -> int:
    # Raw SQL insert because the live DB schema carries extra NOT NULL columns
    # (plan_generation_status, ai_generated_plan, plan_metadata) that are not in
    # the ORM model. This keeps the seed robust against that schema drift.
    import json

    result = await session.execute(
        text(
            """
            INSERT INTO test_definitions
                (name, description, test_id, url, environment, tags, test_context,
                 plan_generation_status, ai_generated_plan, plan_metadata,
                 version, is_active, is_regression, is_draft, review_status,
                 execution_mode, script_status, script_metadata, created_at, updated_at)
            VALUES
                (:name, :description, :test_id, :url, CAST(:environment AS jsonb),
                 :tags, '{}'::jsonb,
                 'none', '{}'::jsonb, '{}'::jsonb,
                 1, true, false, false, 'draft',
                 'script', 'none', '{}'::jsonb, now(), now())
            RETURNING id
            """
        ),
        {
            "name": name,
            "description": description,
            "test_id": test_id,
            "url": url,
            "environment": json.dumps(environment),
            "tags": ["demo", "root-cause"],
        },
    )
    return int(result.scalar_one())


async def _add_run_with_case(
    session,
    def_id: int,
    run_id: str,
    when: datetime,
    passed: bool,
    error_message: str | None,
    case_description: str,
):
    status = "passed" if passed else "failed"
    duration = random.randint(1500, 6000)
    run = TestRun(
        test_definition_id=def_id,
        run_id=run_id,
        status=status,
        start_time=_ms(when),
        end_time=_ms(when + timedelta(milliseconds=duration)),
        total_duration=duration,
        total_tests=1,
        passed=1 if passed else 0,
        failed=0 if passed else 1,
        skipped=0,
        error_message=None if passed else error_message,
        created_at=when,
    )
    session.add(run)
    await session.flush()

    case = TestCase(
        run_id=run.id,
        test_definition_id=def_id,
        test_id=run_id,
        description=case_description,
        status=status,
        duration=duration,
        start_time=_ms(when),
        end_time=_ms(when + timedelta(milliseconds=duration)),
        error_message=None if passed else error_message,
        screenshot_path=None if passed else f"/app/screenshots/{run_id}.png",
        created_at=when,
    )
    session.add(case)


async def seed():
    async with async_session_maker() as session:
        logger.info("Cleaning up previous demo data ...")
        await _cleanup(session)

        now = datetime.utcnow()
        base = now - timedelta(days=40)

        # --- Scenario 1: Regression ---
        reg_id = await _make_definition(
            session,
            name="Login Flow (Regression Demo)",
            test_id=REG_TID,
            url="https://demo.example.com/login",
            environment={"name": "production", "browser": "chromium"},
            description="Login regression scenario for causal demo",
        )
        for i in range(40):
            when = base + timedelta(days=i, hours=2)
            # Deploy at day 25 introduces a regression.
            if i < 25:
                passed = random.random() < 0.95
            else:
                passed = random.random() < 0.30
            await _add_run_with_case(
                session,
                reg_id,
                run_id=f"{REG_TID}-{i:03d}",
                when=when,
                passed=passed,
                error_message=TIMEOUT_ERR,
                case_description="Click login button [env=production] [browser=chromium]",
            )
        logger.info("Seeded regression scenario (40 runs).")

        # --- Scenario 2: Flaky ---
        flaky_id = await _make_definition(
            session,
            name="Search Results (Flaky Demo)",
            test_id=FLAKY_TID,
            url="https://demo.example.com/search",
            environment={"name": "production", "browser": "chromium"},
            description="Flaky search scenario for causal demo",
        )
        for i in range(36):
            when = base + timedelta(days=i + 2, hours=5)
            # Alternate pass/fail with light noise so the pass rate stays ~50%
            # and is temporally stable (no change point) -> genuinely flaky.
            base_pass = (i % 2 == 0)
            passed = (not base_pass) if random.random() < 0.15 else base_pass
            await _add_run_with_case(
                session,
                flaky_id,
                run_id=f"{FLAKY_TID}-{i:03d}",
                when=when,
                passed=passed,
                error_message=SELECTOR_ERR,
                case_description="Verify search results [env=production] [browser=chromium]",
            )
        logger.info("Seeded flaky scenario (36 runs).")

        # --- Scenario 3: Environment issue (chromium ok, firefox fails) ---
        env_id = await _make_definition(
            session,
            name="Checkout Flow (Environment Demo)",
            test_id=ENV_TID,
            url="https://demo.example.com/checkout",
            environment={"name": "production", "browser": "mixed"},
            description="Environment-specific checkout scenario for causal demo",
        )
        idx = 0
        for i in range(40):
            when = base + timedelta(days=i % 30, hours=8, minutes=i)
            browser = "chromium" if i % 2 == 0 else "firefox"
            if browser == "chromium":
                passed = random.random() < 0.93
            else:
                passed = random.random() < 0.20
            await _add_run_with_case(
                session,
                env_id,
                run_id=f"{ENV_TID}-{idx:03d}",
                when=when,
                passed=passed,
                error_message=FIREFOX_ERR,
                case_description=f"Complete checkout [env=production] [browser={browser}]",
            )
            idx += 1
        logger.info("Seeded environment scenario (40 runs).")

        await session.commit()
        logger.info(
            "Done. Demo run_id prefixes: %s, %s, %s",
            REG_TID, FLAKY_TID, ENV_TID,
        )
        logger.info(
            "Example analyze calls:\n"
            "  GET /api/v1/analysis/root-cause/run/%s-039  (regression)\n"
            "  GET /api/v1/analysis/root-cause/run/%s-035  (flaky)\n"
            "  GET /api/v1/analysis/root-cause/run/%s-039  (env issue)",
            REG_TID, FLAKY_TID, ENV_TID,
        )


if __name__ == "__main__":
    asyncio.run(seed())
