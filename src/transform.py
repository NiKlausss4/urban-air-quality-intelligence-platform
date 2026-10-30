import pandas as pd
import numpy as np

POLLUTANTS = {"pm25": "PM2.5", "pm2.5": "PM2.5", "pm10": "PM10", "no2": "NO2", "so2": "SO2", "co": "CO", "o3": "O3", "ozone": "O3"}
CANONICAL = {"PM2.5": "µg/m³", "PM10": "µg/m³", "NO2": "µg/m³", "SO2": "µg/m³", "CO": "µg/m³", "O3": "µg/m³"}
MOLECULAR_WEIGHT = {"NO2": 46.0055, "SO2": 64.066, "CO": 28.01, "O3": 48.00}

def normalize_measurements(rows, city, station_lookup=None):
    good, rejected, seen = [], [], set()
    station_lookup = station_lookup or {}
    for row in rows:
        try:
            parameter = str(row["parameter_name"]).strip().lower()
            code = POLLUTANTS.get(parameter)
            value = float(row["value"])
            dt = pd.to_datetime(row["collected_at"])
            if pd.isna(dt):
                raise ValueError("missing or invalid observation timestamp")
            if dt.tzinfo is None:
                dt = dt.tz_localize("Asia/Kolkata")
            dt = dt.tz_convert("UTC")
            station_id = str(row["station_id"])
            if not code:
                raise ValueError(f"unsupported pollutant: {parameter}")
            if not np.isfinite(value) or value < 0:
                raise ValueError("measurement must be finite and non-negative")
            unit = str(row.get("unit") or "").strip()
            if unit.lower() in {"mg/m³", "mg/m3"}:
                value *= 1000
            elif unit.lower() in {"ppm", "ppb"} and code in MOLECULAR_WEIGHT:
                # Ideal-gas conversion at 25 °C and 1 atm (molar volume 24.45 L/mol).
                value *= (1 if unit.lower() == "ppm" else 0.001) * MOLECULAR_WEIGHT[code] / 24.45 * 1000
            elif unit.lower() not in {"µg/m³", "ug/m3", "μg/m³", "µg/m3", "ug/m³"}:
                raise ValueError(f"unsupported unit: {unit}")
            key = (station_id, code, dt.isoformat())
            if key in seen:
                continue
            seen.add(key)
            station = station_lookup.get(station_id, {})
            good.append({"city": city, "station_source_id": station_id, "sensor_source_id": station_id, "station_name": station.get("station_name", station_id), "latitude": station.get("latitude"), "longitude": station.get("longitude"), "pollutant": code, "observed_at": dt.to_pydatetime(), "value": value, "unit": CANONICAL[code], "raw": row})
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            rejected.append({"city": city, "reason": str(exc), "raw": row})
    return good, rejected

def normalize_weather(payload, city):
    hourly = payload.get("hourly", {})
    output = []
    for i, timestamp in enumerate(hourly.get("time", [])):
        code = _at(hourly, "weather_code", i)
        output.append({"city": city, "observed_at": pd.Timestamp(timestamp, tz="UTC").to_pydatetime(), "temperature_c": _at(hourly, "temperature_2m", i), "relative_humidity": _at(hourly, "relative_humidity_2m", i), "wind_speed_kmh": _at(hourly, "wind_speed_10m", i), "precipitation_mm": _at(hourly, "precipitation", i), "weather_code": None if code is None else int(code)})
    return output

def _at(data, key, index):
    value = data.get(key, [None])[index]
    return None if value is None else float(value)
