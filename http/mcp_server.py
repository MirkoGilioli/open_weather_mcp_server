import os
import requests
from typing import Optional, Tuple
import logging
import asyncio
from fastmcp import FastMCP

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"



logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)


app = FastMCP("openweather-mcp")

# --- Helpers ---
_geocode_cache = {}

def geocode_city(city: str) -> Optional[Tuple[float, float]]:
    """Use the OpenWeather Geocoding API to find coordinates for a city.

    Results are cached in memory to avoid repeated API calls for the same city.

    Args:
        city: The name of the city to geocode.

    Returns:
        A tuple of (latitude, longitude) or None if the city cannot be found.
    """
    if city in _geocode_cache:
        return _geocode_cache[city]
    params = {"q": city, "limit": 1, "appid": OPENWEATHER_API_KEY}
    r = requests.get(GEOCODING_URL, params=params, timeout=10)
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


@app.tool()
async def get_weather(city: str) -> str:
    """
    Fetch current weather for a city using OpenWeather (via geocoding).

    Args:
        city: The name of the city (e.g., "London", "Tokyo").
    """
    coords = geocode_city(city)
    if not coords:
        return f"Could not resolve city '{city}'"
    lat, lon = coords
    r = requests.get(WEATHER_URL, params={"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"}, timeout=10)
    if r.status_code != 200:
        return f"Weather API failed: {r.text}"
    return format_weather_short(r.json())


if __name__ == "__main__":
    logger.info(f"MCP Server started on port {os.getenv('PORT',8080)}")
    asyncio.run(
        app.run_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=os.getenv("PORT", 8080),
        )
    )
