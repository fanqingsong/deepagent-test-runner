"""
Redis-backed job metadata store for test execution jobs.

Replaces in-process dict storage so job state survives API restarts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_JOB_KEY_PREFIX = "job:"
_JOB_INDEX_KEY = "job:index"
_JOB_TTL_SECONDS = 86400


def _client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


class JobStore:
    """
    Redis-backed job metadata store.

    Provides structured job persistence with TTL and indexing.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize JobStore.

        Args:
            redis_client: Optional Redis client. If None, creates default client.
        """
        self.redis_client = redis_client or _client()

    def save_job(self, job_id: str, payload: Dict[str, Any]) -> None:
        """Persist job metadata with 24h TTL."""
        self.redis_client.setex(
            f"{_JOB_KEY_PREFIX}{job_id}",
            _JOB_TTL_SECONDS,
            json.dumps(payload)
        )
        self.redis_client.zadd(
            _JOB_INDEX_KEY,
            {job_id: datetime.utcnow().timestamp()}
        )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Load job metadata or None if missing/expired."""
        raw = self.redis_client.get(f"{_JOB_KEY_PREFIX}{job_id}")
        if not raw:
            return None
        return json.loads(raw)

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Merge updates into stored job metadata."""
        job = self.get_job(job_id)
        if job is None:
            return None
        job.update(updates)
        self.save_job(job_id, job)
        return job

    def list_jobs(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List jobs newest-first."""
        job_ids = self.redis_client.zrevrange(_JOB_INDEX_KEY, skip, skip + limit - 1)
        jobs: List[Dict[str, Any]] = []
        for job_id in job_ids:
            job = self.get_job(job_id)
            if job:
                jobs.append(job)
        return jobs


# Module-level functions for backward compatibility
def save_job(job_id: str, payload: Dict[str, Any]) -> None:
    """Persist job metadata with 24h TTL."""
    client = _client()
    client.setex(f"{_JOB_KEY_PREFIX}{job_id}", _JOB_TTL_SECONDS, json.dumps(payload))
    client.zadd(_JOB_INDEX_KEY, {job_id: datetime.utcnow().timestamp()})


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Load job metadata or None if missing/expired."""
    raw = _client().get(f"{_JOB_KEY_PREFIX}{job_id}")
    if not raw:
        return None
    return json.loads(raw)


def update_job(job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Merge updates into stored job metadata."""
    job = get_job(job_id)
    if job is None:
        return None
    job.update(updates)
    save_job(job_id, job)
    return job


def list_jobs(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """List jobs newest-first."""
    client = _client()
    job_ids = client.zrevrange(_JOB_INDEX_KEY, skip, skip + limit - 1)
    jobs: List[Dict[str, Any]] = []
    for job_id in job_ids:
        job = get_job(job_id)
        if job:
            jobs.append(job)
    return jobs


def save_job(job_id: str, payload: Dict[str, Any]) -> None:
    """Persist job metadata with 24h TTL."""
    client = _client()
    client.setex(f"{_JOB_KEY_PREFIX}{job_id}", _JOB_TTL_SECONDS, json.dumps(payload))
    client.zadd(_JOB_INDEX_KEY, {job_id: datetime.utcnow().timestamp()})


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Load job metadata or None if missing/expired."""
    raw = _client().get(f"{_JOB_KEY_PREFIX}{job_id}")
    if not raw:
        return None
    return json.loads(raw)


def update_job(job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Merge updates into stored job metadata."""
    job = get_job(job_id)
    if job is None:
        return None
    job.update(updates)
    save_job(job_id, job)
    return job


def list_jobs(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """List jobs newest-first."""
    client = _client()
    job_ids = client.zrevrange(_JOB_INDEX_KEY, skip, skip + limit - 1)
    jobs: List[Dict[str, Any]] = []
    for job_id in job_ids:
        job = get_job(job_id)
        if job:
            jobs.append(job)
    return jobs
