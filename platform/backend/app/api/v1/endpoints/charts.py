"""Chart image serving endpoint."""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "charts")


@router.get("/charts/{filename}", include_in_schema=False)
async def get_chart(filename: str):
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    filepath = os.path.join(CHARTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(filepath, media_type="image/png")
