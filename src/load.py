import json
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

def engine(url):
    return create_engine(url, pool_pre_ping=True)

def initialize(db):
    from pathlib import Path
    sql = Path(__file__).resolve().parents[1].joinpath("sql/init.sql").read_text(encoding="utf-8")
    with db.begin() as conn:
        for statement in sql.split(";"):
            if statement.strip(): conn.execute(text(statement))

def save_raw(conn, source, city, payload):
    return conn.execute(text("INSERT INTO raw_api_response(source,city,retrieved_at,payload) VALUES(:s,:c,now(),CAST(:p AS jsonb)) RETURNING raw_id"), {"s": source, "c": city, "p": json.dumps(payload, default=str)}).scalar_one()

def save_reject(conn, source, city, reason, payload):
    conn.execute(text("INSERT INTO rejected_record(source,city,rejected_at,reason,payload) VALUES(:s,:c,now(),:r,CAST(:p AS jsonb))"), {"s": source, "c": city, "r": reason, "p": json.dumps(payload, default=str)})

def upsert_city(conn, name, lat, lon):
    return conn.execute(text("INSERT INTO dim_city(name,latitude,longitude) VALUES(:n,:a,:o) ON CONFLICT(name) DO UPDATE SET latitude=excluded.latitude,longitude=excluded.longitude RETURNING city_id"), {"n": name, "a": lat, "o": lon}).scalar_one()

def load_air(conn, city_id, row, raw_id):
    station_id = conn.execute(text("INSERT INTO dim_station(source_id,city_id,name,latitude,longitude) VALUES(:sid,:cid,:name,:lat,:lon) ON CONFLICT(source_id) DO UPDATE SET city_id=excluded.city_id,name=excluded.name,latitude=excluded.latitude,longitude=excluded.longitude RETURNING station_id"), {"sid": str(row["station_source_id"]), "cid": city_id, "name": row.get("station_name", str(row["station_source_id"])), "lat": row.get("latitude"), "lon": row.get("longitude")}).scalar_one()
    pollutant_id = conn.execute(text("INSERT INTO dim_pollutant(code,canonical_unit) VALUES(:p,:u) ON CONFLICT(code) DO UPDATE SET canonical_unit=excluded.canonical_unit RETURNING pollutant_id"), {"p": row["pollutant"], "u": row["unit"]}).scalar_one()
    conn.execute(text("INSERT INTO dim_date(date_id,date_value,year,month,day) VALUES(:id,:d,:y,:m,:day) ON CONFLICT(date_id) DO NOTHING"), {"id": int(row["observed_at"].strftime("%Y%m%d")), "d": row["observed_at"].date(), "y": row["observed_at"].year, "m": row["observed_at"].month, "day": row["observed_at"].day})
    conn.execute(text("INSERT INTO fact_air_quality(source_id,station_id,city_id,pollutant_id,observed_at,value,unit,anomaly,raw_id) VALUES(:source,:station,:city,:pollutant,:at,:value,:unit,:anomaly,:raw) ON CONFLICT(source_id,pollutant_id,observed_at) DO UPDATE SET station_id=excluded.station_id,city_id=excluded.city_id,value=excluded.value,unit=excluded.unit,raw_id=excluded.raw_id"), {"source": str(row["sensor_source_id"]), "station": station_id, "city": city_id, "pollutant": pollutant_id, "at": row["observed_at"], "value": row["value"], "unit": row["unit"], "anomaly": row["value"] > 150 if row["pollutant"] in ("PM2.5", "PM10") else False, "raw": raw_id})

def load_weather(conn, city_id, row, raw_id):
    conn.execute(text("INSERT INTO fact_weather(city_id,observed_at,temperature_c,relative_humidity,wind_speed_kmh,precipitation_mm,weather_code,raw_id) VALUES(:c,:t,:temp,:rh,:wind,:precip,:code,:raw) ON CONFLICT(city_id,observed_at) DO UPDATE SET temperature_c=excluded.temperature_c,relative_humidity=excluded.relative_humidity,wind_speed_kmh=excluded.wind_speed_kmh,precipitation_mm=excluded.precipitation_mm,weather_code=excluded.weather_code,raw_id=excluded.raw_id"), {"c": city_id, "t": row["observed_at"], "temp": row["temperature_c"], "rh": row["relative_humidity"], "wind": row["wind_speed_kmh"], "precip": row["precipitation_mm"], "code": row["weather_code"], "raw": raw_id})
