import time

import pytest
from fastapi.testclient import TestClient

import app.alerts as alerts
import app.routing as routing
import app.settings as S
import app.trips as trips
from app.geo import dist_to_polyline_m, haversine_m, resample
from app.main import app, model

client = TestClient(app)
PATH = [[20.3553, 85.8189], [20.3488, 85.8241], [20.3402, 85.8272], [20.3299, 85.8302], [20.2961, 85.8245]]


# ---------- geo ----------
def test_haversine_and_polyline():
    assert 1050 < haversine_m(20.0, 85.0, 20.0095, 85.0) < 1070
    d, _ = dist_to_polyline_m(20.3488, 85.8241, PATH)
    assert d < 1
    d, _ = dist_to_polyline_m(20.3488 + 0.002, 85.8241, PATH)       # ~220 m off
    assert 100 < d < 230   # perpendicular distance to a diagonal segment
    pts = resample(PATH, 200)
    assert pts[0] == PATH[0] and pts[-1] == PATH[-1] and len(pts) > 20


# ---------- model ----------
def test_model_loaded_and_health():
    h = client.get("/api/health").json()
    assert h["model_ready"] and h["engine"] == "model" and h["defaults_from_training_data"]


def test_score_endpoint_matches_notebook_pipeline():
    row = {"road_class": "major_road", "ward_id": "W10", "time_of_day": "night", "road_length_km": 0.15,
           "population_density_per_km2": 7000, "police_distance_km": 5.0, "nearest_station_total_cases_2024": 300,
           "street_lights_per_km": 180, "crowd_safety_rating": 3.5, "cctv_coverage_pct": 60,
           "estimated_emergency_response_min": 10, "traffic_level": 0.6, "pedestrian_activity_index": 0.5,
           "estimated_daily_trips": 1200, "reported_safety_incidents_30d": 5}
    r = client.post("/api/score", json={"rows": [row]})
    assert r.status_code == 200 and 0 <= r.json()["scores"][0] <= 100
    # brighter + fewer incidents must not score lower than the opposite
    good = {**row, "street_lights_per_km": 240, "reported_safety_incidents_30d": 0}
    bad = {**row, "street_lights_per_km": 30, "reported_safety_incidents_30d": 15}
    s = client.post("/api/score", json={"rows": [good, bad]}).json()["scores"]
    assert s[0] > s[1]
    # unknown ward must not crash (handle_unknown='ignore')
    assert client.post("/api/score", json={"rows": [{**row, "ward_id": "W999"}]}).status_code == 200
    assert client.post("/api/score", json={"rows": [{"road_class": "x"}]}).status_code == 422


def test_time_label_uses_trained_categories():
    assert model.time_label(23) == "night" and model.time_label(8) == "morning" and model.time_label(14) == "afternoon"


# ---------- route analysis (OSRM/Nominatim unreachable in tests -> demo fallback) ----------
def test_analyze_falls_back_and_ranks(monkeypatch):
    async def none(*a, **k): return None
    monkeypatch.setattr(routing, "osrm_routes", none)
    monkeypatch.setattr(routing, "geocode", none)
    r = client.post("/api/routes/analyze", json={"origin": {"lat": 20.3553, "lng": 85.8189}, "destination_text": "x", "hour": 21}).json()
    assert r["source"] == "demo" and r["engine"] == "model" and len(r["routes"]) == 3
    sc = {x["id"]: x["score"] for x in r["routes"]}
    assert sc["r1"] > sc["r3"] > sc["r2"], sc            # same ordering as the mock UI's intent
    assert r["routes"][0]["tag"] == "Recommended" and r["routes"][0]["id"] == "r1"
    assert r["routes"][0]["risk"] and len(r["routes"][0]["factors"]) == 4
    # night should not be safer than morning for the same route
    m = client.post("/api/routes/analyze", json={"origin": {"lat": 20.3553, "lng": 85.8189}, "destination_text": "x", "hour": 9}).json()
    assert {x["id"]: x["score"] for x in m["routes"]}["r1"] >= sc["r1"]


def test_osrm_parsing():
    import asyncio, httpx
    js = {"code": "Ok", "routes": [{"distance": 6400, "duration": 1140, "legs": [{"summary": "Patia Road"}],
          "geometry": {"coordinates": [[85.8189, 20.3553], [85.8241, 20.3488], [85.8245, 20.2961]]}}]}
    tr = httpx.MockTransport(lambda req: httpx.Response(200, json=js))
    async def go():
        async with httpx.AsyncClient(transport=tr) as c:
            return await routing.osrm_routes({"lat": 20.35, "lng": 85.81}, {"lat": 20.29, "lng": 85.82}, "cab", client=c)
    out = asyncio.run(go())
    assert out[0]["name"] == "Via Patia Road" and out[0]["path"][0] == [20.3553, 85.8189] and out[0]["minutes"] == 19


def test_crowd_ratings_change_score():
    base = client.post("/api/routes/analyze", json={"origin": {"lat": 20.3553, "lng": 85.8189}, "destination_text": "x", "hour": 21}).json()
    r2 = [x for x in base["routes"] if x["id"] == "r2"][0]
    lat, lng = r2["risk"][5][0], r2["risk"][5][1]
    for _ in range(3):
        assert client.post("/api/ratings", json={"lat": lat, "lng": lng, "rating": 1}).status_code == 200
    assert client.post("/api/ratings", json={"lat": lat, "lng": lng, "rating": 9}).status_code == 422
    after = client.post("/api/routes/analyze", json={"origin": {"lat": 20.3553, "lng": 85.8189}, "destination_text": "x", "hour": 21}).json()
    r2b = [x for x in after["routes"] if x["id"] == "r2"][0]
    assert r2b["score"] <= r2["score"]


# ---------- trip state machine (pure logic with injected time) ----------
def mk(mode="cab", contacts=None, risk=None):
    return trips.create(mode, PATH, risk or [], contacts or [{"name": "A", "phone": "9876543210"}], "Test", "Route", now=1000.0)


def feed(t, pts, start=1000.0, dt=4.0, acc=10):
    now = start
    for lat, lng in pts:
        now += dt
        trips.ping(t, lat, lng, acc, now)
        acts = trips.evaluate(t, now)
    return now, acts


def test_on_route_stays_normal_and_arrival():
    t = mk()
    now, _ = feed(t, resample(PATH, 60)[:-3])
    assert t.level == 0 and t.deviation_m < 20
    trips.ping(t, *PATH[-1], 10, now + 4)
    assert t.status == "completed"


def test_deviation_then_graded_escalation():
    t = mk()
    off = [(p[0] + 0.003, p[1]) for p in resample(PATH, 60)[5:12]]          # ~330 m off
    now, _ = feed(t, off)
    assert t.level == 1 and t.reason == "off_route"
    acts = trips.evaluate(t, now + S.CHECKIN_SECONDS + 1)
    assert t.level == 2 and acts == ["notify_contacts"]
    assert trips.evaluate(t, now + S.CHECKIN_SECONDS + 2) == []            # no duplicate alert
    acts = trips.evaluate(t, now + S.CHECKIN_SECONDS + S.CONTACTS_TO_CONTROL_S + 2)
    assert t.level == 3 and acts == ["control_room"]


def test_checkin_resets_and_cooldown_prevents_retrigger():
    t = mk()
    off = [(p[0] + 0.003, p[1]) for p in resample(PATH, 60)[5:12]]
    now, _ = feed(t, off)
    assert t.level == 1
    assert trips.confirm_safe(t, now) is False                              # contacts not yet alerted
    assert t.level == 0
    trips.ping(t, off[-1][0], off[-1][1], 10, now + 4)
    assert trips.evaluate(t, now + 5) == [] and t.level == 0                # cooldown holds


def test_poor_gps_accuracy_does_not_trigger():
    t = mk()
    off = [(p[0] + 0.003, p[1]) for p in resample(PATH, 60)[5:12]]
    feed(t, off, acc=400)
    assert t.level == 0


def test_stall_detection_and_pickup_exemption():
    t = mk(risk=[[p[0], p[1], 40] for p in resample(PATH, 200)])            # low-safety zone -> 60 s threshold
    spot = resample(PATH, 60)[20]
    now, _ = feed(t, [tuple(spot)] * 16)                                    # ~64 s still
    assert t.level == 1 and t.reason == "stalled"
    t2 = mk()                                                               # waiting at pickup is fine
    feed(t2, [tuple(PATH[0])] * 80)
    assert t2.level == 0


def test_signal_lost():
    t = mk()
    feed(t, resample(PATH, 60)[:5])
    trips.evaluate(t, 1000 + 20 + S.SIGNAL_LOST_S + 5)
    assert t.level == 1 and t.reason == "signal_lost"


def test_sos_and_safe_notifies_contacts():
    t = mk()
    assert trips.sos(t, 2000.0) == ["notify_contacts"] and t.level == 2
    assert trips.sos(t, 2001.0) == []
    assert trips.confirm_safe(t, 2002.0) is True





# ---------- HTTP trip flow + alerts ----------
def test_trip_http_flow_and_auth(monkeypatch):
    sent = []
    async def fake_notify(t, kind="alert", client=None): sent.append(kind); return []
    monkeypatch.setattr(alerts, "notify_contacts", fake_notify)
    r = client.post("/api/trips", json={"mode": "cab", "route_name": "R", "path": PATH, "contacts": [{"name": "A", "phone": "98765 43210"}], "user_name": "Asha"}).json()
    tid, tok = r["trip_id"], r["token"]
    h = {"X-Trip-Token": tok}
    assert client.get(f"/api/trips/{tid}").status_code == 404                       # no token
    assert client.get(f"/api/trips/{tid}", headers={"X-Trip-Token": "bad"}).status_code == 404
    s = client.post(f"/api/trips/{tid}/location", json={"lat": 20.3553, "lng": 85.8189, "accuracy": 8}, headers=h).json()
    assert s["level"] == 0 and s["position"] == [20.3553, 85.8189]
    s = client.post(f"/api/trips/{tid}/sos", headers=h).json()
    assert s["level"] == 2 and s["contact_links"][0]["tel"] == "tel:+919876543210" and "wa.me/919876543210" in s["contact_links"][0]["whatsapp"]
    assert sent == ["alert"]
    s = client.post(f"/api/trips/{tid}/checkin", headers=h).json()
    assert s["level"] == 0 and sent == ["alert", "safe"]
    client.post(f"/api/trips/{tid}/end", headers=h)
    assert client.get(f"/api/trips/{tid}", headers=h).status_code == 404             # data deleted on end


def test_alert_channels_with_mocked_http(monkeypatch):
    import asyncio, httpx
    monkeypatch.setattr(S, "TELEGRAM_BOT_TOKEN", "tok")
    calls = []
    def handler(req):
        calls.append((str(req.url), req.content.decode()))
        return httpx.Response(200, json={"ok": True})
    t = trips.create("cab", PATH, [], [{"name": "A", "phone": "", "telegram_chat_id": "555"}], "Asha", "R", now=1.0)
    t.reason, t.last_pos = "off_route", (20.35, 85.82)
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await alerts.notify_contacts(t, "alert", client=c)
    res = asyncio.run(go())
    assert res == [{"contact": "A", "channel": "telegram", "ok": True}]
    assert "api.telegram.org/bottok/sendMessage" in calls[0][0] and "555" in calls[0][1] and "google.com/maps" in calls[0][1]


def test_telegram_link_flow(monkeypatch):
    monkeypatch.setattr(S, "TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setattr(S, "TELEGRAM_BOT_USERNAME", "RaahiBot")
    async def noreply(*a, **k): pass
    monkeypatch.setattr(alerts, "telegram_reply", noreply)
    link = client.post("/api/telegram/link").json()
    assert link["deep_link"] == f"https://t.me/RaahiBot?start={link['code']}"
    assert client.get(f"/api/telegram/link/{link['code']}").json() == {"linked": False, "chat_id": None}
    client.post("/api/telegram/webhook", json={"message": {"text": f"/start {link['code']}", "chat": {"id": 4242}}})
    assert client.get(f"/api/telegram/link/{link['code']}").json() == {"linked": True, "chat_id": "4242"}
    client.post("/api/telegram/webhook", json={"message": {"text": f"/start {link['code']}", "chat": {"id": 9999}}})   # replay can't hijack
    assert client.get(f"/api/telegram/link/{link['code']}").json()["chat_id"] == "4242"
    assert client.get("/api/telegram/link/nope").status_code == 404
