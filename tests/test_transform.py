from src.transform import normalize_measurements, normalize_weather

def test_measurement_normalization_and_duplicate_handling():
    row={"station_id":"site_1","parameter_name":"PM2.5","unit":"mg/m³","value":0.012,"collected_at":"2025-09-01T00:00:00","source":"cpcb_caaqm"}
    stations={"site_1":{"station_name":"Test station","latitude":12.0,"longitude":77.0}}
    good,bad=normalize_measurements([row,row],"Bengaluru",stations)
    assert len(good)==1 and not bad
    assert good[0]["value"]==12
    assert good[0]["observed_at"].isoformat()=="2025-08-31T18:30:00+00:00"

def test_invalid_measurement_is_retained_as_rejected():
    good,bad=normalize_measurements([{"station_id":"site_1","parameter_name":"PM2.5","unit":"µg/m³","value":-1,"collected_at":"2025-09-01T00:00:00"}],"Mumbai")
    assert not good and len(bad)==1 and bad[0]["reason"]

def test_weather_arrays_become_hourly_records():
    data={"hourly":{"time":["2025-01-01T00:00"],"temperature_2m":[20],"relative_humidity_2m":[60],"wind_speed_10m":[5],"precipitation":[0],"weather_code":[1]}}
    out=normalize_weather(data,"Bengaluru")
    assert len(out)==1 and out[0]["temperature_c"]==20 and out[0]["relative_humidity"]==60
