"""
Weather API Endpoints

Provides weather data for cities (currently Nanjing).
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.services.weather_service import get_nanjing_weather, WeatherServiceError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/nanjing")
async def get_nanjing_weather_endpoint():
    """
    Get current weather and forecast for Nanjing.

    Returns:
        - Current weather (temperature, humidity, wind, etc.)
        - Air quality index (AQI)
        - UV index
        - 7-day forecast

    Note: Uses QWeather API if configured, otherwise returns mock data.
    """
    try:
        weather_data = await get_nanjing_weather()
        return JSONResponse(
            content=weather_data.to_dict(),
            headers={
                "Cache-Control": "public, max-age=600",  # Cache for 10 minutes
            }
        )
    except WeatherServiceError as e:
        logger.error(f"Weather service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Weather service temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in weather endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/health")
async def weather_health_check():
    """Health check endpoint for weather service."""
    try:
        # Try to fetch weather data
        weather_data = await get_nanjing_weather()

        return {
            "status": "healthy",
            "provider": "configured" if weather_data else "mock",
            "last_update": "success",
            "city": weather_data.city if weather_data else "unknown"
        }
    except Exception as e:
        logger.error(f"Weather health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )
