import asyncio
import hmac
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from . import alerts, routing, scoring, settings, store, trips
from .model import SafetyModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("raahi")
IST = timezone(timedelta(hours=5, minutes=30))

model = SafetyModel(settings.MODEL_DIR)
provider = scoring.GeoFeatureProvider(settings.DATA_DIR / "geo_features.csv")


async def _perform(t, actions):
    for a in actions:
        if a == "notify_contacts":
            await alerts.notify_contacts(t, "alert")
        elif a == "control_room":
            await alerts.control_room(t)


async def _monitor_loop():
    """Escalation must fire even if the phone stops pinging, so evaluate every active trip every 5s."""
    while True:
        await asyncio.sleep(5)
        for t in list(trips.TRIPS.values()):
            try:
                await _perform(t, trips.evaluate(t))
            except Exception:
                log.exception("monitor error")


@asynccontextmanager
async def lifespan(_):
    task = asyncio.create_task(_monitor_loop())
    yield
    task.cancel()


app = FastAPI(title="Raahi Safety API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


# ---------- models ----------
class Point(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class AnalyzeReq(BaseModel):
    origin: Point
    destination: Optional[Point] = None
    destination_text: Optional[str] = Field(None, max_length=200)
    mode: str = Field("cab", pattern="^(cab|walk)$")
    hour: Optional[int] = Field(None, ge=0, le=23)


class Contact(BaseModel):
    name: str = Field("", max_length=60)
    phone: str = Field("", max_length=20)
    telegram_chat_id: Optional[str] = None


class TripReq(BaseModel):
    mode: str = Field("cab", pattern="^(cab|walk)$")
    route_name: str = Field("", max_length=100)
    path: List[List[float]] = Field(min_length=2, max_length=3000)
    risk: List[List[float]] = Field(default_factory=list, max_length=500)
    contacts: List[Contact] = Field(default_factory=list, max_length=8)
    user_name: str = Field("", max_length=60)


class LocReq(Point):
    accuracy: Optional[float] = None


class RatingReq(Point):
    rating: float = Field(ge=1, le=5)


class ScoreReq(BaseModel):
    rows: List[dict] = Field(min_length=1, max_length=500)


def _trip(trip_id, token):
    t = trips.TRIPS.get(trip_id)
    if not t or not token or not hmac.compare_digest(token, t.token):
        raise HTTPException(404, "trip not found")
    return t


def _full_state(t):
    s = trips.state(t)
    if t.level >= 2:
        s["contact_links"] = alerts.contact_links(t)
    return s


# ---------- general ----------
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/api/health")
def health():
    return {"status": "ok", "model_ready": model.ready, "model_error": model.error,
            "engine": "model" if model.ready else "heuristic",
            "defaults_from_training_data": model.defaults_from_data,
            "geo_feature_points": provider.n,
            "channels": {"telegram": bool(settings.TELEGRAM_BOT_TOKEN),
                         "twilio": bool(settings.TWILIO_SID and settings.TWILIO_FROM),
                         "control_room_webhook": bool(settings.CONTROL_ROOM_WEBHOOK_URL)},
            "active_trips": sum(1 for t in trips.TRIPS.values() if t.status == "active")}


@app.post("/api/score")
def score_rows(req: ScoreReq):
    """Direct access to your trained model: send rows with the 15 training features, get scores 0-100."""
    if not model.ready:
        raise HTTPException(503, f"model not loaded: {model.error}")
    try:
        return {"scores": [round(s, 2) for s in model.predict(req.rows)]}
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/geocode")
async def geocode(q: str):
    res = await routing.geocode(q)
    if not res:
        raise HTTPException(404, "place not found")
    return res


# ---------- route analysis ----------
@app.post("/api/routes/analyze")
async def analyze(req: AnalyzeReq):
    dest = req.destination.model_dump() if req.destination else None
    if dest is None and req.destination_text:
        g = await routing.geocode(req.destination_text)
        dest = {"lat": g["lat"], "lng": g["lng"]} if g else None
    candidates = await routing.osrm_routes(req.origin.model_dump(), dest, req.mode) if dest else None
    source = "osrm"
    if not candidates:
        candidates, source = routing.DEMO_ROUTES, "demo"
    hour = req.hour if req.hour is not None else datetime.now(IST).hour
    results = scoring.rank_routes([scoring.score_route(c, hour, model, provider) for c in candidates])
    return {"source": source, "engine": results[0]["engine"], "hour": hour, "routes": results}


# ---------- live trips ----------
@app.post("/api/trips")
def start_trip(req: TripReq):
    t = trips.create(req.mode, req.path, req.risk, [c.model_dump() for c in req.contacts], req.user_name, req.route_name)
    return {"trip_id": t.id, "token": t.token, "state": _full_state(t)}


@app.post("/api/trips/{trip_id}/location")
async def post_location(trip_id: str, loc: LocReq, x_trip_token: str = Header(None)):
    t = _trip(trip_id, x_trip_token)
    trips.ping(t, loc.lat, loc.lng, loc.accuracy)
    await _perform(t, trips.evaluate(t))
    return _full_state(t)


@app.get("/api/trips/{trip_id}")
def get_trip(trip_id: str, x_trip_token: str = Header(None)):
    return _full_state(_trip(trip_id, x_trip_token))


@app.post("/api/trips/{trip_id}/checkin")
async def checkin(trip_id: str, x_trip_token: str = Header(None)):
    t = _trip(trip_id, x_trip_token)
    if trips.confirm_safe(t):
        await alerts.notify_contacts(t, "safe")
    return _full_state(t)


@app.post("/api/trips/{trip_id}/sos")
async def sos(trip_id: str, x_trip_token: str = Header(None)):
    t = _trip(trip_id, x_trip_token)
    await _perform(t, trips.sos(t))
    return _full_state(t)


@app.post("/api/trips/{trip_id}/end")
async def end_trip(trip_id: str, x_trip_token: str = Header(None)):
    t = _trip(trip_id, x_trip_token)
    if trips.end(t):
        await alerts.notify_contacts(t, "safe")
    s = _full_state(t)
    trips.TRIPS.pop(trip_id, None)   # delete location data as soon as the trip ends
    return s


# ---------- crowd ratings ----------
@app.post("/api/ratings")
def rate(req: RatingReq):
    store.add_rating(req.lat, req.lng, req.rating)
    return {"ok": True}


# ---------- telegram contact linking ----------
@app.post("/api/telegram/link")
def tg_link():
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_BOT_USERNAME:
        raise HTTPException(503, "Telegram bot not configured")
    code = store.new_link_code()
    return {"code": code, "deep_link": f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={code}"}


@app.get("/api/telegram/link/{code}")
def tg_link_status(code: str):
    chat = store.get_link(code)
    if chat is None:
        raise HTTPException(404, "unknown code")
    return {"linked": bool(chat), "chat_id": chat or None}


@app.post("/api/telegram/webhook")
async def tg_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    if settings.TELEGRAM_WEBHOOK_SECRET and not hmac.compare_digest(x_telegram_bot_api_secret_token or "", settings.TELEGRAM_WEBHOOK_SECRET):
        raise HTTPException(403, "bad secret")
    upd = await request.json()
    msg = upd.get("message") or {}
    text, chat = (msg.get("text") or "").strip(), (msg.get("chat") or {}).get("id")
    if chat and text.startswith("/start "):
        if store.set_link(text.split(" ", 1)[1].strip(), chat):
            await alerts.telegram_reply(chat, "Linked. You'll get a message here if your friend's Raahi trip raises a safety alert.")
        else:
            await alerts.telegram_reply(chat, "That link has expired or was already used. Ask your friend for a new one.")
    return {"ok": True}
