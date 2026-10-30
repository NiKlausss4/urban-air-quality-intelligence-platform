from datetime import datetime, timedelta, timezone
import time
import requests

XKDR = "https://airquality.xkdr.org/v1"
METEO = "https://archive-api.open-meteo.com/v1/archive"
POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "Ozone"]

class APIError(RuntimeError):
    pass

def _get(url, *, params=None, headers=None, timeout=30):
    for attempt in range(4):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 3:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(2 ** (attempt + 1), 30)
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            if attempt == 3:
                raise APIError(f"GET {url} failed after retries: {exc}") from exc
            time.sleep(min(2 ** attempt, 8))

def _auth(api_key):
    api_key = (api_key or "").strip()
    if not api_key:
        raise APIError("XKDR_API_KEY is required; configure it in .env")
    if "\r" in api_key or "\n" in api_key:
        raise APIError("XKDR_API_KEY contains an embedded newline; replace it in the deployment settings")
    return {"Authorization": f"Bearer {api_key}"}

def stations(city, api_key):
    response = _get(f"{XKDR}/stations", params={"city": city, "format": "json"}, headers=_auth(api_key))
    payload = response.json()
    return payload.get("data", [])

def measurements(city, api_key, start_date, end_date):
    params = [("city", city), ("start", start_date.isoformat()), ("end", end_date.isoformat()), ("agg", "raw"), ("format", "json")]
    params.extend(("parameter", pollutant) for pollutant in POLLUTANTS)
    response = _get(f"{XKDR}/measurements", params=params, headers=_auth(api_key), timeout=90)
    payload = response.json()
    meta = payload.get("meta", {})
    truncated = response.headers.get("X-Truncated", "").lower() == "true" or meta.get("truncated") is True
    if truncated:
        raise APIError(f"xKDR truncated {city} measurement query at {meta.get('max_rows', 'the configured row cap')}; narrow the date window")
    return payload.get("data", []), payload

def weather(latitude, longitude, start, end):
    params = {"latitude": latitude, "longitude": longitude, "start_date": start.date().isoformat(), "end_date": end.date().isoformat(), "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code", "timezone": "UTC", "wind_speed_unit": "kmh"}
    return _get(METEO, params=params).json()

def latest_station_date(station_rows):
    dates = [datetime.fromisoformat(row["last_seen"]).date() for row in station_rows if row.get("last_seen")]
    if not dates:
        return None
    return max(dates)

def default_start(hours):
    return datetime.now(timezone.utc) - timedelta(hours=hours)
