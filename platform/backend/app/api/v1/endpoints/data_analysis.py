"""Data Analysis API Endpoints — Upload files, execute analysis, retrieve results."""

import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app.services.data_analysis_service import (
    upload_file,
    start_analysis,
    get_analysis_results,
    AnalysisRequest,
    MAX_UPLOAD_SIZE,
)

logger = logging.getLogger(__name__)

router = APIRouter()
CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "agents", "charts")


@router.get("/config")
async def get_data_analysis_config():
    """Return data analysis feature config."""
    return {
        "enabled": True,
        "max_upload_size": MAX_UPLOAD_SIZE,
        "allowed_formats": ["csv", "json", "txt"],
        "chart_types": ["bar", "line", "scatter", "histogram", "pie", "box", "heatmap"],
        "analysis_types": ["summary", "correlation", "distribution", "missing"],
    }


@router.post("/upload")
async def upload_data_file(
    file: UploadFile = File(..., description="Data file for analysis (CSV/JSON, max 50MB)"),
    user_id: Optional[int] = Query(None, description="User ID for workspace isolation"),
):
    """Upload a data file (CSV/JSON) for analysis.

    The file is stored in the user's isolated workspace and can be analyzed
    using the /analyze endpoint.
    """
    # Validate file size
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE // 1024 // 1024}MB"
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Validate file format
    filename = file.filename or "uploaded_file"
    file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if file_ext not in ["csv", "json", "txt"]:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file format: {file_ext}. Allowed: csv, json, txt"
        )

    try:
        result = upload_file(file_content=content, filename=filename, user_id=user_id)
        return {
            "success": True,
            "file_id": result["file_id"],
            "filename": result["filename"],
            "size": len(content),
            "message": "File uploaded successfully. Use the file_id in /analyze to start analysis.",
        }
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/analyze")
async def analyze_data(request: AnalysisRequest):
    """Start data analysis on an uploaded file.

    Args:
        request: Analysis request with file_id, prompt, and options

    Returns:
        Analysis job ID for tracking results
    """
    try:
        result = start_analysis(request)
        return {
            "success": True,
            "job_id": result["job_id"],
            "status": result["status"],
            "message": "Analysis started. Use /results/{job_id} to retrieve results.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed to start: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/results/{job_id}")
async def get_results(job_id: str):
    """Retrieve analysis results by job ID.

    Args:
        job_id: Analysis job ID returned from /analyze

    Returns:
        Analysis results including generated charts
    """
    try:
        results = get_analysis_results(job_id)

        if results.get("status") == "pending":
            return {
                "job_id": job_id,
                "status": "pending",
                "message": "Analysis is in progress..."
            }
        elif results.get("status") == "running":
            return {
                "job_id": job_id,
                "status": "running",
                "message": "Analysis is running..."
            }
        elif results.get("status") == "failed":
            return {
                "job_id": job_id,
                "status": "failed",
                "error": results.get("error", "Analysis failed"),
            }
        else:
            return {
                "job_id": job_id,
                "status": results.get("status"),
                "result": results.get("result"),
                "charts": results.get("charts", []),
            }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    except Exception as e:
        logger.error(f"Failed to retrieve results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")


@router.get("/charts/{filename}")
async def get_chart(filename: str):
    """Serve generated chart images.

    Args:
        filename: Chart filename (e.g., "chart_abc123.png")

    Returns:
        Chart image file
    """
    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = os.path.join(CHARTS_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Chart not found")

    return FileResponse(
        filepath,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete analysis job and cleanup files.

    Args:
        job_id: Analysis job ID to delete

    Returns:
        Confirmation of deletion
    """
    try:
        from app.services.data_analysis_service import delete_analysis_job
        delete_analysis_job(job_id)
        return {
            "success": True,
            "job_id": job_id,
            "message": "Job deleted successfully"
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")
