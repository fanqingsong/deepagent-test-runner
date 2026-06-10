"""
Monitoring Storage Service

Handles persistence of monitoring snapshots and retrieval of historical data.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import get_db, sync_session_maker
from app.models.monitoring import AgentMonitoring

logger = logging.getLogger(__name__)


def _get_sync_db() -> Session:
    """Get a synchronous database session for use in agent tools."""
    return sync_session_maker()


async def save_monitoring_snapshot(metrics: Dict[str, Any], status: str = "normal", db: Optional[AsyncSession] = None) -> Optional[int]:
    """
    Save a monitoring snapshot to the database.

    Args:
        metrics: Collected metrics dictionary
        status: Overall system status (normal, warning, critical)
        db: Database session (optional, if None will create one)

    Returns:
        ID of the created snapshot, or None if failed
    """
    # If no session provided, this is for backward compatibility but not recommended for Temporal
    if db is None:
        logger.warning("save_monitoring_snapshot called without db session, this should not happen in Temporal context")
        return None

    try:
        snapshot = AgentMonitoring(
            check_time=datetime.utcnow(),
            status=status,
            metrics=metrics,
            report_summary=None,  # Will be populated by AI reporter
        )

        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)

        logger.info("Saved monitoring snapshot: id=%d, status=%s", snapshot.id, status)
        return snapshot.id

    except Exception as e:
        logger.error("Failed to save monitoring snapshot: %s", e)
        await db.rollback()
        return None


async def get_latest_snapshot() -> Optional[Dict[str, Any]]:
    """
    Get the most recent monitoring snapshot.

    Returns:
        Dict with snapshot data or None if no snapshots exist
    """
    db = _get_sync_db()

    try:
        snapshot = db.execute(
            select(AgentMonitoring)
            .order_by(AgentMonitoring.check_time.desc())
            .limit(1)
        ).scalar_one_or_none()

        if not snapshot:
            return None

        return {
            "id": snapshot.id,
            "check_time": snapshot.check_time.isoformat() if snapshot.check_time else None,
            "status": snapshot.status,
            "metrics": snapshot.metrics,
            "alerts_generated": snapshot.alerts_generated,
            "report_summary": snapshot.report_summary,
            "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        }

    except Exception as e:
        logger.error("Failed to get latest snapshot: %s", e)
        return None

    finally:
        db.close()


async def get_historical_metrics(days: int = 7) -> List[Dict[str, Any]]:
    """
    Get historical monitoring snapshots for trend analysis.

    Args:
        days: Number of days of history to retrieve

    Returns:
        List of snapshot dicts ordered by check_time descending
    """
    db = _get_sync_db()

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = db.execute(
            select(AgentMonitoring)
            .where(AgentMonitoring.check_time >= cutoff_date)
            .order_by(AgentMonitoring.check_time.desc())
        )
        snapshots = result.scalars().all()

        results = []
        for snapshot in snapshots:
            results.append({
                "id": snapshot.id,
                "check_time": snapshot.check_time.isoformat() if snapshot.check_time else None,
                "status": snapshot.status,
                "metrics": snapshot.metrics,
                "report_summary": snapshot.report_summary,
            })

        logger.info("Retrieved %d historical snapshots (last %d days)", len(results), days)
        return results

    except Exception as e:
        logger.error("Failed to get historical metrics: %s", e)
        return []

    finally:
        db.close()


async def update_snapshot_report(snapshot_id: int, report_summary: str) -> bool:
    """
    Update a snapshot with AI-generated report summary.

    Args:
        snapshot_id: ID of the snapshot to update
        report_summary: AI-generated summary text

    Returns:
        True if successful, False otherwise
    """
    db = _get_sync_db()

    try:
        snapshot = db.execute(
            select(AgentMonitoring).where(AgentMonitoring.id == snapshot_id)
        ).scalar_one_or_none()

        if not snapshot:
            logger.warning("Snapshot %d not found for report update", snapshot_id)
            return False

        snapshot.report_summary = report_summary
        db.commit()

        logger.info("Updated snapshot %d with report summary", snapshot_id)
        return True

    except Exception as e:
        logger.error("Failed to update snapshot report: %s", e)
        db.rollback()
        return False

    finally:
        db.close()


async def get_snapshot_for_comparison(hours_ago: int = 24) -> Optional[Dict[str, Any]]:
    """
    Get a snapshot from a specific time ago for comparison.

    Args:
        hours_ago: How many hours back to look (default: 24h for day-over-day)

    Returns:
        Snapshot dict or None if not found
    """
    db = _get_sync_db()

    try:
        target_time = datetime.utcnow() - timedelta(hours=hours_ago)

        # Find the closest snapshot within ±2 hours
        snapshot = db.execute(
            select(AgentMonitoring)
            .where(AgentMonitoring.check_time >= target_time - timedelta(hours=2))
            .where(AgentMonitoring.check_time <= target_time + timedelta(hours=2))
            .order_by(AgentMonitoring.check_time.desc())
            .limit(1)
        ).scalar_one_or_none()

        if not snapshot:
            return None

        return {
            "id": snapshot.id,
            "check_time": snapshot.check_time.isoformat() if snapshot.check_time else None,
            "status": snapshot.status,
            "metrics": snapshot.metrics,
        }

    except Exception as e:
        logger.error("Failed to get comparison snapshot: %s", e)
        return None

    finally:
        db.close()
