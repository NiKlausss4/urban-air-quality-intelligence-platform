import os
import pytest
from src.load import engine, initialize, upsert_city, load_air

@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="set TEST_DATABASE_URL to run PostgreSQL integration coverage")
def test_fact_load_is_idempotent():
    db=engine(os.environ["TEST_DATABASE_URL"])
    initialize(db)
    with db.connect() as conn:
        tx=conn.begin()
        try:
            city_id=upsert_city(conn,"__integration_test_city__",1.0,2.0)
            row={"station_source_id":"site_integration_1","sensor_source_id":"site_integration_1","station_name":"Integration Test Station","observed_at":__import__("datetime").datetime(2025,1,1,tzinfo=__import__("datetime").timezone.utc),"pollutant":"PM2.5","value":12.0,"unit":"µg/m³"}
            load_air(conn,city_id,row,None)
            load_air(conn,city_id,row,None)
            count=conn.exec_driver_sql("SELECT count(*) FROM fact_air_quality WHERE source_id='site_integration_1' AND observed_at='2025-01-01T00:00:00+00:00'").scalar_one()
            assert count==1
        finally:
            tx.rollback()
