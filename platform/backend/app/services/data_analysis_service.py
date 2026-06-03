"""Data Analysis Service — Business logic for file upload and analysis execution."""

import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional
from datetime import datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configuration
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
UPLOAD_DIR = "/tmp/data_analysis_uploads"
JOBS: Dict[str, Dict] = {}
executor = ThreadPoolExecutor(max_workers=4)


class AnalysisRequest(BaseModel):
    """Request model for data analysis."""

    file_id: str
    prompt: str
    analysis_type: Optional[str] = "custom"
    user_id: Optional[int] = None
    chart_types: Optional[list] = None


def upload_file(file_content: bytes, filename: str, user_id: Optional[int] = None) -> Dict:
    """Upload and store a data file for analysis.

    Args:
        file_content: File content as bytes
        filename: Original filename
        user_id: Optional user ID for isolation

    Returns:
        Dict with file_id and stored filename
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_id = uuid.uuid4().hex[:16]
    safe_filename = f"{file_id}_{filename}"
    filepath = os.path.join(UPLOAD_DIR, safe_filename)

    with open(filepath, "wb") as f:
        f.write(file_content)

    return {
        "file_id": file_id,
        "filename": safe_filename,
        "filepath": filepath,
        "size": len(file_content),
    }


def get_uploaded_file(file_id: str) -> Dict:
    """Retrieve uploaded file metadata by ID.

    Args:
        file_id: File ID from upload

    Returns:
        File metadata dict

    Raises:
        FileNotFoundError: If file not found
    """
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(f"{file_id}_"):
            filepath = os.path.join(UPLOAD_DIR, filename)
            return {
                "file_id": file_id,
                "filename": filename,
                "filepath": filepath,
                "size": os.path.getsize(filepath),
            }

    raise FileNotFoundError(f"File {file_id} not found")


def start_analysis(request: AnalysisRequest) -> Dict:
    """Start data analysis in background.

    Args:
        request: Analysis request

    Returns:
        Job metadata with job_id
    """
    # Get file metadata
    try:
        file_meta = get_uploaded_file(request.file_id)
    except FileNotFoundError as e:
        raise ValueError(f"File not found: {request.file_id}") from e

    # Create job
    job_id = uuid.uuid4().hex[:16]
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "file_id": request.file_id,
        "file_path": file_meta["filepath"],
        "filename": file_meta["filename"],
        "prompt": request.prompt,
        "analysis_type": request.analysis_type,
        "user_id": request.user_id,
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
        "charts": [],
        "error": None,
    }

    # Start analysis in background
    executor.submit(_run_analysis, job_id, request)

    return {
        "job_id": job_id,
        "status": "pending",
    }


def _run_analysis(job_id: str, request: AnalysisRequest):
    """Execute analysis in background thread.

    Args:
        job_id: Job identifier
        request: Analysis request
    """
    try:
        job = JOBS[job_id]
        job["status"] = "running"
        job["started_at"] = datetime.utcnow().isoformat()

        # Import agent here to avoid circular imports
        from app.core.agent_config import get_llm
        from app.agents.chat_assistant.subagents.sandbox_data_analysis_agent import (
            get_sandbox_data_analysis_subagent,
        )

        # Create agent with user-specific backend
        llm = get_llm(temperature=0.3)
        agent = get_sandbox_data_analysis_subagent(llm=llm, user_id=request.user_id)

        # Prepare input message
        prompt = f"""Analyze the data file at: {job['file_path']}

User request: {request.prompt}

Additional context:
- File ID: {request.file_id}
- Analysis type: {request.analysis_type}

Please:
1. Load and inspect the data
2. Perform the requested analysis
3. Generate relevant visualizations
4. Provide clear insights and findings

Use the file operations tools to read the data, then use execute_python or the analysis tools."""

        # Invoke agent
        result = agent.runnable.invoke({"messages": [{"role": "user", "content": prompt}]})

        # Extract final response
        if result and "messages" in result:
            final_message = result["messages"][-1].content
        else:
            final_message = str(result)

        # Update job with results
        job["status"] = "completed"
        job["result"] = final_message
        job["completed_at"] = datetime.utcnow().isoformat()

        # Extract chart references from result
        # Charts are saved with URLs like /api/v1/charts/{filename}
        import re
        chart_urls = re.findall(r'/api/v1/charts/[\w\-\.]+\.png', final_message)
        job["charts"] = [{"url": url, "filename": url.split("/")[-1]} for url in chart_urls]

        logger.info(f"Analysis job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Analysis job {job_id} failed: {e}")
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = datetime.utcnow().isoformat()


def get_analysis_results(job_id: str) -> Dict:
    """Get analysis results by job ID.

    Args:
        job_id: Job identifier

    Returns:
        Job results dict

    Raises:
        FileNotFoundError: If job not found
    """
    if job_id not in JOBS:
        raise FileNotFoundError(f"Job {job_id} not found")

    return JOBS[job_id]


def delete_analysis_job(job_id: str):
    """Delete analysis job and cleanup.

    Args:
        job_id: Job identifier to delete

    Raises:
        FileNotFoundError: If job not found
    """
    if job_id not in JOBS:
        raise FileNotFoundError(f"Job {job_id} not found")

    job = JOBS[job_id]

    # Cleanup uploaded file if exists
    if "file_path" in job and os.path.exists(job["file_path"]):
        try:
            os.remove(job["file_path"])
        except Exception as e:
            logger.warning(f"Failed to delete file {job['file_path']}: {e}")

    # Delete job record
    del JOBS[job_id]

    logger.info(f"Job {job_id} deleted")


def cleanup_old_jobs(max_age_hours: int = 24):
    """Clean up old completed jobs.

    Args:
        max_age_hours: Maximum age in hours for jobs to keep
    """
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    jobs_to_delete = []

    for job_id, job in JOBS.items():
        if job["status"] in ["completed", "failed"]:
            completed_at = job.get("completed_at", job.get("created_at", ""))
            if completed_at:
                try:
                    completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    if completed_dt < cutoff:
                        jobs_to_delete.append(job_id)
                except ValueError:
                    pass

    for job_id in jobs_to_delete:
        try:
            delete_analysis_job(job_id)
        except Exception as e:
            logger.warning(f"Failed to delete old job {job_id}: {e}")

    if jobs_to_delete:
        logger.info(f"Cleaned up {len(jobs_to_delete)} old jobs")
