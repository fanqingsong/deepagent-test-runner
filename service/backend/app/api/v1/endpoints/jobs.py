"""
Jobs API Endpoints

Test execution job management and monitoring.
"""

import logging
import uuid
from datetime import datetime
from typing import List

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import get_db
from app.core.job_store import get_job, list_jobs, save_job, update_job
from app.schemas.jobs import JobCreate, JobResponse, JobStatusResponse
from app.services import get_execution_service
from app.tasks.test_execution import execute_test

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job_data: JobCreate, db: AsyncSession = Depends(get_db)):
    """
    Create and execute a new test job.

    - **test_definition_ids**: List of test definition IDs to execute
    - **environment**: Environment variables for tests
    - **priority**: Job priority (1-10)
    - **scheduled**: Whether this is a scheduled job
    """
    job_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    try:
        await get_execution_service().create_test_run(
            run_id=job_id,
            test_definition_ids=job_data.test_definition_ids,
            environment=job_data.environment or {},
            db=db,
        )
    except Exception as e:
        logger.warning("Failed to create test run record for job %s: %s", job_id, e)

    task_ids = []
    for test_def_id in job_data.test_definition_ids:
        task = execute_test.delay(test_def_id, job_id, job_data.environment)
        task_ids.append(task.id)

    job_payload = {
        "job_id": job_id,
        "status": "running",
        "test_definition_ids": job_data.test_definition_ids,
        "created_at": created_at,
        "started_at": created_at,
        "completed_at": None,
        "results": None,
        "environment": job_data.environment,
        "task_ids": task_ids,
    }
    save_job(job_id, job_payload)

    return JobResponse(**{k: v for k, v in job_payload.items() if k != "task_ids"})


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of a job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    completed_tasks = 0
    total_tasks = len(job.get("task_ids", []))
    results = []

    for task_id in job.get("task_ids", []):
        result = AsyncResult(task_id, app=celery_app)
        if result.ready():
            completed_tasks += 1
            if result.successful():
                results.append(result.result)

    progress = completed_tasks / total_tasks if total_tasks > 0 else 1.0

    if completed_tasks == total_tasks and total_tasks > 0:
        job = update_job(
            job_id,
            {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "results": {"test_runs": results},
            },
        ) or job

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=progress,
        message=f"{completed_tasks}/{total_tasks} tests completed",
        results=job.get("results"),
    )


@router.get("/", response_model=List[JobResponse])
async def list_jobs_endpoint(skip: int = 0, limit: int = 100):
    """List all jobs."""
    jobs = list_jobs(skip=skip, limit=limit)
    return [
        JobResponse(**{k: v for k, v in job.items() if k != "task_ids"})
        for job in jobs
    ]


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(job_id: str):
    """Cancel a running job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if job["status"] not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status {job['status']}",
        )

    for task_id in job.get("task_ids", []):
        celery_app.control.revoke(task_id, terminate=True)

    update_job(
        job_id,
        {
            "status": "cancelled",
            "completed_at": datetime.utcnow().isoformat(),
        },
    )

    return None
