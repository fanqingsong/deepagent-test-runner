"""
Weather Service - Fetches weather data from external APIs

Supports multiple weather providers:
- QWeather (和风天气) - Recommended for China
- OpenWeatherMap - Global coverage
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Weather data model."""
    city: str
    city_en: str
    temperature: float
    feels_like: float
    weather: str
    weather_en: str
    humidity: int
    wind_speed: float
    wind_direction: str
    pressure: int
    visibility: float
    uv_index: int
    aqi: int
    aqi_level: str
    forecast: list[dict]

    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            "city": self.city,
            "city_en": self.city_en,
            "temperature": self.temperature,
            "feels_like": self.feels_like,
            "weather": self.weather,
            "weather_en": self.weather_en,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "pressure": self.pressure,
            "visibility": self.visibility,
            "uv_index": self.uv_index,
            "aqi": self.aqi,
            "aqi_level": self.aqi_level,
            "forecast": self.forecast
        }


class WeatherServiceError(Exception):
    """Weather service specific error."""
    pass


class QWeatherProvider:
    """QWeather (和风天气) API provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://devapi.qweather.com/v7"
        self.geo_url = "https://geoapi.qweather.com/v2"

    async def get_city_id(self, city_name: str) -> Optional[str]:
        """Get city ID from city name."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.geo_url}/city/lookup",
                    params={"location": city_name, "key": self.api_key},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                if data.get("code") == "200" and data.get("location"):
                    return data["location"][0]["id"]
                return None
            except Exception as e:
                logger.error(f"Failed to get city ID: {e}")
                return None

    async def get_current_weather(self, location_id: str) -> dict:
        """Get current weather data."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/weather/now",
                params={"location": location_id, "key": self.api_key},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "200":
                raise WeatherServiceError(f"Weather API error: {data.get('code')}")

            return data["now"]

    async def get_weather_forecast(self, location_id: str, days: int = 7) -> list:
        """Get weather forecast."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/weather/{days}d",
                params={"location": location_id, "key": self.api_key},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "200":
                raise WeatherServiceError(f"Forecast API error: {data.get('code')}")

            return data.get("daily", [])

    async def get_air_quality(self, location_id: str) -> dict:
        """Get air quality data."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/air/now",
                params={"location": location_id, "key": self.api_key},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "200":
                logger.warning(f"Air quality API error: {data.get('code')}")
                return None

            return data.get("now", {})

    async def fetch_nanjing_weather(self) -> WeatherData:
        """Fetch complete weather data for Nanjing."""
        try:
            # Get Nanjing location ID (101190101)
            location_id = "101190101"  # Pre-defined for Nanjing

            # Fetch all data concurrently
            current, forecast, air_quality = await asyncio.gather(
                self.get_current_weather(location_id),
                self.get_weather_forecast(location_id, days=7),
                self.get_air_quality(location_id),
                return_exceptions=True
            )

            # Handle any errors
            if isinstance(current, Exception):
                raise WeatherServiceError(f"Failed to get current weather: {current}")
            if isinstance(forecast, Exception):
                logger.warning(f"Failed to get forecast: {forecast}")
                forecast = []
            if isinstance(air_quality, Exception):
                logger.warning(f"Failed to get air quality: {air_quality}")
                air_quality = None

            # Map weather codes to descriptions
            weather_map = {
                "100": {"zh": "晴", "en": "Sunny", "icon": "sun"},
                "101": {"zh": "多云", "en": "Cloudy", "icon": "cloud"},
                "102": {"zh": "少云", "en": "Partly Cloudy", "icon": "cloud"},
                "103": {"zh": "晴间多云", "en": "Mostly Sunny", "icon": "sun"},
                "104": {"zh": "阴", "en": "Overcast", "icon": "cloud"},
                "200": {"zh": "小雨", "en": "Light Rain", "icon": "rain"},
                "201": {"zh": "中雨", "en": "Moderate Rain", "icon": "rain"},
                "202": {"zh": "大雨", "en": "Heavy Rain", "icon": "rain"},
                "300": {"zh": "小雪", "en": "Light Snow", "icon": "rain"},
                "301": {"zh": "中雪", "en": "Moderate Snow", "icon": "rain"},
                "302": {"zh": "大雪", "en": "Heavy Snow", "icon": "rain"},
            }

            weather_info = weather_map.get(current.get("icon", "100"), weather_map["100"])

            # Process forecast data
            forecast_days = []
            weekday_map = {0: "周日", 1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六"}

            for i, day in enumerate(forecast[:7]):
                date_obj = datetime.strptime(day["fxDate"], "%Y-%m-%d")
                day_name = "今天" if i == 0 else ("明天" if i == 1 else weekday_map.get(date_obj.weekday(), day["fxDate"]))
                day_weather = weather_map.get(day.get("iconDay", "100"), weather_map["100"])

                forecast_days.append({
                    "day": day_name,
                    "high": int(day["tempMax"]),
                    "low": int(day["tempMin"]),
                    "weather": day_weather["zh"],
                    "icon": day_weather["icon"]
                })

            # Process air quality
            aqi = air_quality.get("aqi", 50) if air_quality else 50
            aqi_level = "优" if aqi <= 50 else ("良" if aqi <= 100 else ("轻度污染" if aqi <= 150 else "中度污染"))

            return WeatherData(
                city="南京",
                city_en="Nanjing",
                temperature=float(current["temp"]),
                feels_like=float(current["feelsLike"]),
                weather=weather_info["zh"],
                weather_en=weather_info["en"],
                humidity=int(current["humidity"]),
                wind_speed=float(current["windSpeed"]) / 10.0,  # Convert to m/s
                wind_direction=current.get("windDir", "未知"),
                pressure=int(current["pressure"]),
                visibility=float(current["vis"]) / 10.0,  # Convert to km
                uv_index=6,  # Default if not available
                aqi=aqi,
                aqi_level=aqi_level,
                forecast=forecast_days
            )

        except WeatherServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch QWeather data: {e}")
            raise WeatherServiceError(f"Weather service error: {str(e)}")


class OpenWeatherMapProvider:
    """OpenWeatherMap API provider (fallback)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def fetch_nanjing_weather(self) -> WeatherData:
        """Fetch weather data for Nanjing from OpenWeatherMap."""
        try:
            async with httpx.AsyncClient() as client:
                # Get current weather
                response = await client.get(
                    f"{self.base_url}/weather",
                    params={
                        "q": "Nanjing,CN",
                        "appid": self.api_key,
                        "units": "metric",
                        "lang": "zh_cn"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                # Get forecast
                forecast_response = await client.get(
                    f"{self.base_url}/forecast",
                    params={
                        "q": "Nanjing,CN",
                        "appid": self.api_key,
                        "units": "metric",
                        "cnt": 7
                    },
                    timeout=10.0
                )
                forecast_response.raise_for_status()
                forecast_data = forecast_response.json()

                # Map weather conditions
                weather_id = data["weather"][0]["id"]
                if weather_id < 300:
                    weather_zh, weather_en, icon = "雷暴", "Thunderstorm", "rain"
                elif weather_id < 500:
                    weather_zh, weather_en, icon = "雨", "Drizzle", "rain"
                elif weather_id < 600:
                    weather_zh, weather_en, icon = "雨", "Rain", "rain"
                elif weather_id < 700:
                    weather_zh, weather_en, icon = "雪", "Snow", "rain"
                elif weather_id == 800:
                    weather_zh, weather_en, icon = "晴", "Clear", "sun"
                else:
                    weather_zh, weather_en, icon = "多云", "Clouds", "cloud"

                # Process forecast
                forecast_days = []
                weekday_map = {0: "周日", 1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六"}

                for i, item in enumerate(forecast_data.get("list", [])[:7]):
                    date_obj = datetime.fromtimestamp(item["dt"])
                    day_name = "今天" if i == 0 else ("明天" if i == 1 else weekday_map.get(date_obj.weekday(), str(i)))

                    temp_max = int(item["main"]["temp_max"])
                    temp_min = int(item["main"]["temp_min"])

                    forecast_days.append({
                        "day": day_name,
                        "high": temp_max,
                        "low": temp_min,
                        "weather": weather_zh,
                        "icon": icon
                    })

                return WeatherData(
                    city="南京",
                    city_en="Nanjing",
                    temperature=round(data["main"]["temp"]),
                    feels_like=round(data["main"]["feels_like"]),
                    weather=weather_zh,
                    weather_en=weather_en,
                    humidity=int(data["main"]["humidity"]),
                    wind_speed=round(data["wind"]["speed"], 1),
                    wind_direction="未知",
                    pressure=int(data["main"]["pressure"]),
                    visibility=round(data["visibility"] / 1000, 1),
                    uv_index=6,
                    aqi=50,
                    aqi_level="良",
                    forecast=forecast_days
                )

        except Exception as e:
            logger.error(f"Failed to fetch OpenWeatherMap data: {e}")
            raise WeatherServiceError(f"Weather service error: {str(e)}")


# Fallback mock data for when no API is configured
def get_mock_weather() -> WeatherData:
    """Return mock weather data for development."""
    return WeatherData(
        city="南京",
        city_en="Nanjing",
        temperature=26,
        feels_like=28,
        weather="晴",
        weather_en="Sunny",
        humidity=65,
        wind_speed=3.5,
        wind_direction="东南风",
        pressure=1013,
        visibility=10.0,
        uv_index=6,
        aqi=78,
        aqi_level="良",
        forecast=[
            {"day": "今天", "high": 28, "low": 20, "weather": "晴", "icon": "sun"},
            {"day": "明天", "high": 29, "low": 21, "weather": "多云", "icon": "cloud"},
            {"day": "后天", "high": 27, "low": 19, "weather": "小雨", "icon": "rain"},
            {"day": "周四", "high": 25, "low": 18, "weather": "多云", "icon": "cloud"},
            {"day": "周五", "high": 26, "low": 19, "weather": "晴", "icon": "sun"},
            {"day": "周六", "high": 28, "low": 20, "weather": "晴", "icon": "sun"},
            {"day": "周日", "high": 27, "low": 19, "weather": "多云", "icon": "cloud"}
        ]
    )


# Service instance
def get_weather_provider():
    """Get configured weather provider based on environment."""
    import os

    # Check for QWeather API key
    qweather_key = os.getenv("QWEATHER_API_KEY")
    if qweather_key and qweather_key != "your-qweather-api-key":
        logger.info("Using QWeather provider")
        return QWeatherProvider(qweather_key)

    # Check for OpenWeatherMap API key
    owm_key = os.getenv("OPENWEATHER_API_KEY")
    if owm_key and owm_key != "your-openweathermap-api-key":
        logger.info("Using OpenWeatherMap provider")
        return OpenWeatherMapProvider(owm_key)

    logger.warning("No weather API configured, using mock data")
    return None


async def get_nanjing_weather() -> WeatherData:
    """
    Get weather data for Nanjing.

    Returns WeatherData from configured provider or mock data.
    """
    provider = get_weather_provider()

    if provider:
        try:
            return await provider.fetch_nanjing_weather()
        except WeatherServiceError as e:
            logger.error(f"Weather provider failed: {e}, falling back to mock data")
            return get_mock_weather()
        except Exception as e:
            logger.error(f"Unexpected error: {e}, falling back to mock data")
            return get_mock_weather()

    return get_mock_weather()
