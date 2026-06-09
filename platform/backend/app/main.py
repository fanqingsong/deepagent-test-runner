"""
FastAPI Application Entry Point

This is a minimal main.py file to support test infrastructure.
The actual API is defined in app/api/v1/api.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings


# Create FastAPI app
app = FastAPI(
    title="DeepAgent Test Runner API",
    description="AI-powered E2E testing framework",
    version="1.0.0"
)

# Configure CORS - SECURITY: Use specific origins from settings, not wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Specific origins only (security fix)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
