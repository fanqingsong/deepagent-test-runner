"""
Monitoring Metric Collector

Gathers system metrics from multiple sources for the monitoring agent.
Collects metrics across 4 categories: Test Execution, LLM Performance, Resources, User Activity.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_usage import LlmUsage
from app.models.monitoring import AgentMonitoring
from app.models.schedule import Schedule
from app.models.test_run import TestRun
from app.models.user import User

logger = logging.getLogger(__name__)


async def collect_test_execution_metrics(db: AsyncSession) -> Dict[str, Any]:
    """
    Collect test execution health metrics.

    Returns:
        Dict with test_runs_24h, failing_tests, schedules status
    """
    now = datetime.utcnow()
    yesterday = now - timedelta(hours=24)

    # Get test runs in last 24 hours
    result = await db.execute(
        select(
            func.count(TestRun.id).label("total"),
            func.sum(func.cast(TestRun.status == "passed", type_=func.INTEGER)).label("passed"),
            func.sum(func.cast(TestRun.status == "failed", type_=func.INTEGER)).label("failed"),
            func.avg(TestRun.total_duration).label("avg_duration"),
        ).where(TestRun.created_at >= yesterday)
    )
    row = result.first()

    total_runs = row.total or 0
    passed_runs = row.passed or 0
    failed_runs = row.failed or 0
    avg_duration = row.avg_duration or 0

    pass_rate = passed_runs / total_runs if total_runs > 0 else 0.0

    # Find failing tests (runs with status='failed' in last 24h)
    failing_runs_result = await db.execute(
        select(TestRun.test_definition_id, TestRun.created_at, TestRun.error_message)
        .where(TestRun.created_at >= yesterday)
        .where(TestRun.status == "failed")
        .order_by(TestRun.created_at.desc())
        .limit(10)
    )
    failing_runs = failing_runs_result.all()

    failing_tests = []
    for run in failing_runs:
        failing_tests.append({
            "test_definition_id": run.test_definition_id,
            "last_failure": run.created_at.isoformat() if run.created_at else None,
            "error_message": run.error_message,
        })

    # Get schedule status
    active_schedules_result = await db.execute(
        select(func.count(Schedule.id)).where(Schedule.is_active == True)
    )
    active_schedules = active_schedules_result.scalar()

    missed_schedules_result = await db.execute(
        select(func.count(Schedule.id))
        .where(Schedule.is_active == True)
        .where(Schedule.next_run_time < yesterday)
    )
    missed_schedules = missed_schedules_result.scalar()

    return {
        "test_runs_24h": {
            "total": total_runs,
            "passed": passed_runs,
            "failed": failed_runs,
            "pass_rate": round(pass_rate, 2),
            "avg_duration_ms": round(avg_duration) if avg_duration else 0,
        },
        "failing_tests": failing_tests,
        "schedules": {
            "active": active_schedules or 0,
            "last_check": now.isoformat(),
            "missed_schedules": missed_schedules or 0,
        },
    }


async def collect_llm_metrics(db: AsyncSession) -> Dict[str, Any]:
    """
    Collect LLM agent performance metrics.

    Returns:
        Dict with token_usage_24h, avg_response_time_ms, slowest_operations
    """
    yesterday = datetime.utcnow() - timedelta(hours=24)

    # Get token usage in last 24 hours
    result = await db.execute(
        select(
            func.sum(LlmUsage.total_tokens).label("total_tokens"),
            func.sum(LlmUsage.duration_ms).label("total_duration"),
            func.count(LlmUsage.id).label("call_count"),
        ).where(LlmUsage.created_at >= yesterday)
    )
    row = result.first()

    total_tokens = row.total_tokens or 0
    total_duration = row.total_duration or 0
    call_count = row.call_count or 0

    avg_response_time = total_duration / call_count if call_count > 0 else 0

    # Get token usage by agent type
    agent_usage_result = await db.execute(
        select(
            LlmUsage.agent_type,
            func.sum(LlmUsage.total_tokens).label("tokens"),
            func.avg(LlmUsage.duration_ms).label("avg_ms"),
        )
        .where(LlmUsage.created_at >= yesterday)
        .group_by(LlmUsage.agent_type)
    )
    agent_usage = agent_usage_result.all()

    by_agent = {}
    slowest_operations = []

    for row in agent_usage:
        agent_name = row.agent_type
        tokens = row.tokens or 0
        avg_ms = row.avg_ms or 0

        by_agent[agent_name] = {
            "tokens": tokens,
            "avg_response_ms": round(avg_ms),
        }

        # Track slowest operations
        if avg_ms > 1000:  # Slower than 1 second
            slowest_operations.append({
                "agent": agent_name,
                "avg_ms": round(avg_ms),
            })

    # Sort slowest by response time
    slowest_operations.sort(key=lambda x: x["avg_ms"], reverse=True)

    # Estimate cost (assuming GLM-4-plus pricing ~$0.01 per 1K tokens)
    estimated_cost = (total_tokens / 1000) * 0.01

    return {
        "token_usage_24h": {
            "total_tokens": total_tokens,
            "by_agent": by_agent,
            "estimated_cost_usd": round(estimated_cost, 2),
        },
        "avg_response_time_ms": round(avg_response_time),
        "slowest_operations": slowest_operations[:5],  # Top 5 slowest
    }


async def collect_resource_metrics(db: AsyncSession) -> Dict[str, Any]:
    """
    Collect system resource metrics.

    Returns:
        Dict with database, temporal, redis status
    """
    # Database connection pool status (simplified - check from engine)
    # In production, use sqlalchemy.engine.status
    try:
        pool_status = await db.execute(select(func.count()))
        result = pool_status.scalar()
        db_healthy = result is not None
    except Exception as e:
        logger.warning("Database health check failed: %s", e)
        db_healthy = False

    # For now, return placeholder data
    # TODO: Integrate with actual connection pool monitoring
    return {
        "database": {
            "status": "healthy" if db_healthy else "unhealthy",
            "connection_pool_used": "N/A",  # Requires engine access
            "slow_queries_last_hour": 0,  # Requires query logging
        },
        "temporal": {
            "status": "unknown",  # Requires Temporal API check
            "workers_active": "N/A",
            "workflows_pending": "N/A",
        },
        "redis": {
            "status": "unknown",  # Requires Redis client
            "job_store_size": "N/A",
        },
    }


async def collect_user_activity_metrics(db: AsyncSession) -> Dict[str, Any]:
    """
    Collect user activity metrics.

    Returns:
        Dict with active_users_24h, api_calls_24h, top_features
    """
    yesterday = datetime.utcnow() - timedelta(hours=24)

    # Active users (users with sessions in last 24h)
    # Note: Requires user_sessions table - using User.last_login as proxy
    active_users_result = await db.execute(
        select(func.count(User.id)).where(and_(User.last_login.isnot(None), User.last_login >= yesterday))
    )
    active_users = active_users_result.scalar()

    # Total users (for context)
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()

    # API calls - placeholder (requires API logging table)
    # Top features - placeholder (requires feature access tracking)

    return {
        "active_users_24h": active_users or 0,
        "total_users": total_users or 0,
        "api_calls_24h": "N/A",  # Requires API logging
        "top_features": ["studio", "dashboard", "schedules"],  # Default based on common usage
    }


async def collect_all_metrics(db: AsyncSession) -> Dict[str, Any]:
    """
    Collect all metrics from all sources.

    Args:
        db: Database session (AsyncSession from Temporal worker context)

    Returns:
        Complete metrics dictionary for monitoring snapshot.
    """
    metrics = {
        "check_time": datetime.utcnow().isoformat(),
        "test_execution": {},
        "llm_performance": {},
        "resources": {},
        "user_activity": {},
    }

    try:
        # Collect metrics from all categories
        metrics["test_execution"] = await collect_test_execution_metrics(db)
        metrics["llm_performance"] = await collect_llm_metrics(db)
        metrics["resources"] = await collect_resource_metrics(db)
        metrics["user_activity"] = await collect_user_activity_metrics(db)

        # Calculate overall system status
        test_status = metrics["test_execution"].get("test_runs_24h", {})
        llm_status = metrics["llm_performance"].get("slowest_operations", [])

        # Determine overall status (simplified logic)
        if test_status.get("pass_rate", 1.0) < 0.8 or len(llm_status) > 3:
            overall_status = "critical"
        elif test_status.get("pass_rate", 1.0) < 0.95 or len(llm_status) > 1:
            overall_status = "warning"
        else:
            overall_status = "normal"

        metrics["overall_status"] = overall_status

        logger.info("Collected monitoring metrics: status=%s", overall_status)

    except Exception as e:
        logger.error("Failed to collect monitoring metrics: %s", e)
        metrics["error"] = str(e)
        metrics["overall_status"] = "unknown"

    return metrics
