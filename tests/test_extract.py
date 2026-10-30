from datetime import date
from src import extract

class Response:
    def __init__(self, body, headers=None):
        self.body=body
        self.status_code=200
        self.headers=headers or {}
    def raise_for_status(self): pass
    def json(self): return self.body

def test_xkdr_measurements_use_bearer_key_and_city_query(monkeypatch):
    calls=[]
    def fake_get(url, params, headers, timeout):
        calls.append((url,params,headers,timeout))
        return Response({"data":[{"station_id":"site_1"}],"meta":{"truncated":False}})
    monkeypatch.setattr(extract.requests,"get",fake_get)
    rows,payload=extract.measurements("Delhi","secret",date(2025,8,26),date(2025,9,1))
    url,params,headers,timeout=calls[0]
    assert rows==payload["data"] and "airquality.xkdr.org/v1/measurements" in url
    assert headers["Authorization"]=="Bearer secret"
    assert ("city","Delhi") in params and ("parameter","PM2.5") in params

def test_xkdr_station_metadata_returns_data_rows(monkeypatch):
    monkeypatch.setattr(extract.requests,"get",lambda *args,**kwargs: Response({"data":[{"station_id":"site_1"}]}))
    assert extract.stations("Bengaluru","secret")==[{"station_id":"site_1"}]

def test_xkdr_truncated_query_fails_loudly(monkeypatch):
    monkeypatch.setattr(extract.requests,"get",lambda *args,**kwargs: Response({"data":[],"meta":{"truncated":True,"max_rows":10}}))
    try:
        extract.measurements("Delhi","secret",date(2025,8,26),date(2025,9,1))
    except extract.APIError as exc:
        assert "truncated" in str(exc)
    else:
        raise AssertionError("expected truncation to fail visibly")

def test_missing_xkdr_key_fails_before_network():
    try:
        extract.stations("Delhi","")
    except extract.APIError as exc:
        assert "XKDR_API_KEY" in str(exc)
    else:
        raise AssertionError("expected missing key to fail")
