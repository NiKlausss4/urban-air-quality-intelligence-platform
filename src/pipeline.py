import json
import logging
import uuid
from datetime import datetime, date, time, timezone, timedelta

from sqlalchemy import text

from .config import settings, CITY_COORDINATES
from .extract import stations, measurements, weather, latest_station_date
from .transform import normalize_measurements, normalize_weather
from .load import engine, initialize, save_raw, save_reject, upsert_city, load_air, load_weather

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("airquality")
IST = timezone(timedelta(hours=5, minutes=30))

def run():
    cfg = settings()
    if not cfg["api_key"]:
        raise ValueError("XKDR_API_KEY is required; add your xKDR key to .env")
    db = engine(cfg["database_url"])
    initialize(db)
    run_id = str(uuid.uuid4())
    extracted = transformed = rejected = duplicates = 0
    with db.begin() as conn:
        conn.execute(text("INSERT INTO pipeline_run(run_id,started_at,status) VALUES(:id,now(),'running')"), {"id": run_id})
    try:
        for city in cfg["cities"]:
            if city not in CITY_COORDINATES:
                raise ValueError(f"Unsupported configured city {city!r}; add coordinates in src/config.py")
            lat, lon = CITY_COORDINATES[city]
            station_rows = stations(city, cfg["api_key"])
            station_lookup = {str(row["station_id"]): row for row in station_rows}
            latest_date = latest_station_date(station_rows) or date.today()
            lookback_days = max(1, (cfg["lookback_hours"] + 23) // 24)
            start_date = latest_date - timedelta(days=lookback_days - 1)
            with db.connect() as conn:
                previous = conn.execute(text("SELECT watermark FROM city_watermark WHERE city=:c AND source='xkdr'"), {"c": city}).scalar_one_or_none()
            if previous is not None:
                previous_date = (previous.astimezone(IST) - timedelta(hours=6)).date()
                start_date = max(start_date, previous_date)
            if start_date > latest_date:
                start_date = latest_date

            rows, air_payload = measurements(city, cfg["api_key"], start_date, latest_date)
            extracted += len(rows)
            good, bad = normalize_measurements(rows, city, station_lookup)
            rejected += len(bad)
            duplicates += max(0, len(rows) - len(good) - len(bad))

            weather_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
            weather_end = datetime.combine(latest_date, time.max, tzinfo=timezone.utc)
            weather_payload = weather(lat, lon, weather_start, weather_end)
            weather_rows = normalize_weather(weather_payload, city)

            with db.begin() as conn:
                city_id = upsert_city(conn, city, lat, lon)
                air_raw_id = save_raw(conn, "xkdr", city, {"stations": station_rows, "measurements": air_payload})
                weather_raw_id = save_raw(conn, "open_meteo", city, weather_payload)
                for item in bad:
                    save_reject(conn, "xkdr", city, item["reason"], item["raw"])
                for item in good:
                    load_air(conn, city_id, item, air_raw_id)
                for item in weather_rows:
                    load_weather(conn, city_id, item, weather_raw_id)
                transformed += len(good) + len(weather_rows)
                watermark = datetime.combine(latest_date, time.max, tzinfo=IST).astimezone(timezone.utc)
                conn.execute(text("INSERT INTO city_watermark(city,source,watermark) VALUES(:c,'xkdr',:w) ON CONFLICT(city,source) DO UPDATE SET watermark=GREATEST(city_watermark.watermark,excluded.watermark)"), {"c": city, "w": watermark})
            log.info("%s: stations=%d, extracted=%d, accepted=%d, rejected=%d, window=%s..%s", city, len(station_rows), len(rows), len(good), len(bad), start_date, latest_date)
            if not good:
                log.warning("No xKDR pollutant observations returned for %s in the available window", city)

        with db.begin() as conn:
            conn.execute(text("UPDATE pipeline_run SET finished_at=now(),status='success',extracted=:e,transformed=:t,rejected=:r,duplicates=:d WHERE run_id=:id"), {"id": run_id, "e": extracted, "t": transformed, "r": rejected, "d": duplicates})
    except Exception as exc:
        log.exception("ETL run %s failed", run_id)
        with db.begin() as conn:
            conn.execute(text("UPDATE pipeline_run SET finished_at=now(),status='failed',extracted=:e,transformed=:t,rejected=:r,duplicates=:d,errors=CAST(:err AS jsonb) WHERE run_id=:id"), {"id": run_id, "e": extracted, "t": transformed, "r": rejected, "d": duplicates, "err": json.dumps([str(exc)])})
        raise

if __name__ == "__main__":
    run()
