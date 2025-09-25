import os
import httpx
from typing import Optional, Tuple
import logging
import asyncio
from datetime import datetime
from fastmcp import FastMCP

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    raise RuntimeError("Set OPENWEATHER_API_KEY environment variable")

GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
AIR_POLLUTION_CURRENT_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
AIR_POLLUTION_FORECAST_URL = "https://api.openweathermap.org/data/2.5/air_pollution/forecast"

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

app = FastMCP("openweather-mcp")

# --- Helpers ---
_geocode_cache = {}

async def geocode_city(city: str) -> Optional[Tuple[float, float]]:
    """Use the OpenWeather Geocoding API to find coordinates for a city.

    This function is async and uses httpx.

    Results are cached in memory to avoid repeated API calls for the same city.

    Args:
        city: The name of the city to geocode.

    Returns:
        A tuple of (latitude, longitude) or None if the city cannot be found.
    """
    if city in _geocode_cache:
        return _geocode_cache[city]
    params = {"q": city, "limit": 1, "appid": OPENWEATHER_API_KEY}
    async with httpx.AsyncClient() as client:
        r = await client.get(GEOCODING_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        lat, lon = data[0]["lat"], data[0]["lon"]
        _geocode_cache[city] = (lat, lon)
        return lat, lon

def format_weather_short(j: dict) -> str:
    """Formats the raw JSON response from the OpenWeather current weather API into a short, human-readable string.

    Extracts city name, country, temperature, and weather description.

    Args:
        j: The JSON dictionary response from the OpenWeather current weather API.

    Returns:
        A formatted string summarizing the current weather, e.g., "London, GB: 15.2°C, clear sky".
    """
    name = j.get("name") or ""
    country = j.get("sys", {}).get("country", "")
    place = f"{name}, {country}".strip(", ")
    temp = j.get("main", {}).get("temp")
    desc = j.get("weather", [{}])[0].get("description", "")
    return f"{place}: {temp}°C, {desc}"

def format_air_pollution_current(j: dict) -> str:
    """
    Format the current air pollution response nicely.
    j is JSON from /air_pollution endpoint.
    """
    try:
        item = j.get("list", [])[0]
        aqi = item["main"]["aqi"]
        comps = item["components"]
        parts = []
        for comp in ["pm2_5", "pm10", "no2", "o3", "so2", "co", "nh3"]:
            if comp in comps:
                parts.append(f"{comp.upper()}={comps[comp]:.2f}")
        return f"AQI: {aqi}. Components: " + ", ".join(parts)
    except Exception:
        return "Unable to parse air pollution data"

def format_air_pollution_forecast(j: dict, limit: int = 5) -> str:
    lines = ["Air pollution forecast:"]
    for entry in j.get("list", [])[:limit]:
        dt = datetime.fromtimestamp(entry["dt"]).strftime("%Y-%m-%d %H:%M")
        aqi = entry["main"]["aqi"]
        comps = entry["components"]
        parts = []
        for comp in ["pm2_5", "pm10", "no2", "o3", "so2", "co", "nh3"]:
            if comp in comps:
                parts.append(f"{comp.upper()}={comps[comp]:.2f}")
        lines.append(f"{dt} — AQI {aqi}: " + ", ".join(parts))
    return "\n".join(lines)

# --- Tools ---

@app.tool()
async def get_weather(city: str) -> str:
    """
    Fetch current weather for a city using OpenWeather (via geocoding).

    Args:
        city: The name of the city (e.g., "London", "Tokyo").
    """
    coords = await geocode_city(city)
    if not coords:
        return f"Could not resolve city '{city}'"
    lat, lon = coords
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    async with httpx.AsyncClient() as client:
        r = await client.get(WEATHER_URL, params=params, timeout=10)
        if r.status_code != 200:
            return f"Weather API failed: {r.text}"
        return format_weather_short(r.json())

@app.tool()
async def get_air_pollution(city: str, forecast: bool = False, limit: int = 5) -> str:
    """Fetch air pollution data for a city.

    Can retrieve either the current air pollution data or a forecast.

    Args:
        city: The name of the city (e.g., "London", "Tokyo").
        forecast: If True, fetch the forecast instead of current data. Defaults to False.
        limit: The number of forecast slots to return (only used if forecast=True). Defaults to 5.
    """
    coords = await geocode_city(city)
    if not coords:
        return f"Could not resolve city '{city}'"
    lat, lon = coords

    url = AIR_POLLUTION_FORECAST_URL if forecast else AIR_POLLUTION_CURRENT_URL
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY}

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return f"Air Pollution API failed: {r.text}"
        j = r.json()

    if forecast:
        return format_air_pollution_forecast(j, limit=limit)
    return format_air_pollution_current(j)

if __name__ == "__main__":
    logger.info(f"MCP Server started on port {os.getenv('PORT',8080)}")
    asyncio.run(
        app.run_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=os.getenv("PORT", 8080),
        )
    )
