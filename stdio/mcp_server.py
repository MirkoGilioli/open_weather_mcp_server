#!/usr/bin/env python3
import os
import requests
from datetime import datetime
from typing import Optional, Tuple
from mcp.server.fastmcp import FastMCP

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
if not API_KEY:
    raise RuntimeError("Set OPENWEATHER_API_KEY environment variable")

GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST5_URL = "https://api.openweathermap.org/data/2.5/forecast"
AIR_POLLUTION_CURRENT_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
AIR_POLLUTION_FORECAST_URL = "https://api.openweathermap.org/data/2.5/air_pollution/forecast"

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
    params = {"q": city, "limit": 1, "appid": API_KEY}
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

def format_forecast5_short(j: dict, limit: int = 5) -> str:
    """Formats the raw JSON response from the 5-day forecast API into a human-readable string.

    Args:
        j: The JSON dictionary response from the OpenWeather 5-day forecast API.
        limit: The maximum number of 3-hour forecast slots to format.

    Returns:
        A formatted, multi-line string summarizing the forecast.
    """
    city = j.get("city", {}).get("name", "Unknown")
    lines = [f"5-day / 3-hour forecast for {city} (first {limit} slots):"]
    for entry in j.get("list", [])[:limit]:
        dt = datetime.fromtimestamp(entry["dt"]).strftime("%Y-%m-%d %H:%M")
        temp = entry["main"]["temp"]
        desc = entry["weather"][0]["description"]
        lines.append(f"{dt}: {temp}°C, {desc}")
    return "\n".join(lines)

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
    city = "unknown"
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
def get_weather(city: str) -> str:
    """
    Fetch current weather for a city using OpenWeather (via geocoding).

    Args:
        city: The name of the city (e.g., "London", "Tokyo").
    """
    coords = geocode_city(city)
    if not coords:
        return f"Could not resolve city '{city}'"
    lat, lon = coords
    r = requests.get(WEATHER_URL, params={"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"}, timeout=10)
    if r.status_code != 200:
        return f"Weather API failed: {r.text}"
    return format_weather_short(r.json())

@app.tool()
def get_forecast_5d(city: str, slots: int = 5) -> str:
    """Fetch 5-day weather forecast for a city.

    The forecast provides data in 3-hour intervals.

    Args:
        city: The name of the city (e.g., "London", "Tokyo").
        slots: The number of 3-hour forecast slots to return. Defaults to 5.
    """
    coords = geocode_city(city)
    if not coords:
        return f"Could not resolve city '{city}'"
    lat, lon = coords
    r = requests.get(FORECAST5_URL, params={"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"}, timeout=10)
    if r.status_code != 200:
        return f"Forecast API failed: {r.text}"
    return format_forecast5_short(r.json(), limit=slots)

@app.tool()
def get_air_pollution(city: str, forecast: bool = False, limit: int = 5) -> str:
    """Fetch air pollution data for a city.

    Can retrieve either the current air pollution data or a forecast.

    Args:
        city: The name of the city (e.g., "London", "Tokyo").
        forecast: If True, fetch the forecast instead of current data. Defaults to False.
        limit: The number of forecast slots to return (only used if forecast=True). Defaults to 5.
    """
    coords = geocode_city(city)
    if not coords:
        return f"Could not resolve city '{city}'"
    lat, lon = coords

    if forecast:
        url = AIR_POLLUTION_FORECAST_URL
    else:
        url = AIR_POLLUTION_CURRENT_URL

    r = requests.get(url, params={"lat": lat, "lon": lon, "appid": API_KEY}, timeout=10)
    if r.status_code != 200:
        return f"Air Pollution API failed: {r.text}"
    j = r.json()

    if forecast:
        return format_air_pollution_forecast(j, limit=limit)
    else:
        return format_air_pollution_current(j)

# --- Run server ---
if __name__ == "__main__":
    app.run()
