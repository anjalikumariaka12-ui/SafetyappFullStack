"""Live-trip monitoring: deviation / stall / signal-loss detection + graded escalation state machine.

  level 0  normal
  level 1  in-app check-in ("Still okay?")        -> after CHECKIN_SECONDS unanswered ->
  level 2  emergency contacts alerted              -> after CONTACTS_TO_CONTROL_S unresolved ->
  level 3  control-room escalation

Pure logic, no network calls: evaluate() returns *actions* that main.py performs. `now` is injectable for tests.
"""
import secrets
import time
from collections import deque
from dataclasses import dataclass, field

from . import settings
from .geo import dist_to_polyline_m, haversine_m


@dataclass
class Trip:
    id: str
    token: str
    mode: str
    path: list
    risk: list              # [[lat,lng,score],...] per-sample safety scores of the chosen route
    contacts: list
    user_name: str
    route_name: str
    created: float
    last_ping: float
    last_pos: tuple = None
    pings: deque = field(default_factory=lambda: deque(maxlen=60))  # (ts, lat, lng)
    status: str = "active"  # active | completed | ended
    level: int = 0
    level_since: float = 0.0
    reason: str = None
    off_count: int = 0
    deviation_m: float = 0.0
    cooldown_until: float = 0.0
    contacts_alerted: bool = False
    control_alerted: bool = False
    events: list = field(default_factory=list)


TRIPS = {}


def _log(t, now, msg):
    t.events.append({"ts": round(now), "msg": msg})
    del t.events[:-20]


def purge(now=None):
    now = now or time.time()
    for k in [k for k, t in TRIPS.items() if now - t.last_ping > settings.TRIP_TTL_S]:
        del TRIPS[k]


def create(mode, path, risk, contacts, user_name, route_name, now=None):
    now = now or time.time()
    purge(now)
    t = Trip(id=secrets.token_urlsafe(8), token=secrets.token_urlsafe(24), mode=mode, path=path, risk=risk or [],
             contacts=contacts, user_name=user_name or "A Raahi user", route_name=route_name, created=now, last_ping=now)
    TRIPS[t.id] = t
    _log(t, now, "Trip started")
    return t


def _local_score(t, lat, lng):
    if not t.risk:
        return None
    best = min(t.risk, key=lambda r: haversine_m(lat, lng, r[0], r[1]))
    return best[2]


def _is_stalled(t, now):
    if not t.pings or t.last_pos is None:
        return False
    score = _local_score(t, *t.last_pos)
    need = settings.STALL_SECONDS_LOW_SAFETY if (score is not None and score < settings.LOW_SAFETY_SCORE) else settings.STALL_SECONDS
    window = [p for p in t.pings if now - p[0] <= need + 15]
    if not window or now - window[0][0] < need - 5:   # not enough history covering the window yet
        return False
    lat, lng = t.last_pos
    if haversine_m(lat, lng, t.path[0][0], t.path[0][1]) <= 150:   # waiting at pickup is normal
        return False
    return all(haversine_m(lat, lng, p[1], p[2]) <= settings.STALL_RADIUS_M for p in window)


def ping(t, lat, lng, accuracy, now=None):
    """Record a GPS fix. Poor-accuracy fixes are stored but not counted as deviation evidence."""
    now = now or time.time()
    if t.status != "active":
        return
    t.last_ping, t.last_pos = now, (lat, lng)
    t.pings.append((now, lat, lng))
    d, _ = dist_to_polyline_m(lat, lng, t.path)
    t.deviation_m = round(d)
    limit = settings.DEVIATION_M_FOOT if t.mode == "walk" else settings.DEVIATION_M_CAB
    if accuracy is not None and accuracy > settings.MIN_ACCURACY_M:
        pass  # unreliable fix: neither add to nor reset the off-route streak
    elif d > limit:
        t.off_count += 1
    else:
        t.off_count = 0
    dest = t.path[-1]
    if haversine_m(lat, lng, dest[0], dest[1]) <= settings.ARRIVAL_M:
        t.status, t.level, t.reason = "completed", 0, None
        _log(t, now, "Reached destination")


def evaluate(t, now=None):
    """Advance the state machine. Returns a list of actions: 'notify_contacts', 'control_room'."""
    now = now or time.time()
    actions = []
    if t.status != "active":
        return actions
    if t.level == 0 and now >= t.cooldown_until:
        reason = None
        if t.off_count >= settings.DEVIATION_PINGS:
            reason = "off_route"
        elif _is_stalled(t, now):
            reason = "stalled"
        elif now - t.last_ping > settings.SIGNAL_LOST_S:
            reason = "signal_lost"
        if reason:
            t.level, t.level_since, t.reason = 1, now, reason
            _log(t, now, f"Check-in sent ({reason})")
    elif t.level == 1 and now - t.level_since >= settings.CHECKIN_SECONDS:
        t.level, t.level_since = 2, now
        _log(t, now, "Check-in unanswered: contacts alerted")
        if not t.contacts_alerted:
            t.contacts_alerted = True
            actions.append("notify_contacts")
    elif t.level == 2 and now - t.level_since >= settings.CONTACTS_TO_CONTROL_S:
        t.level, t.level_since = 3, now
        _log(t, now, "Escalated to control room")
        if not t.control_alerted:
            t.control_alerted = True
            actions.append("control_room")
    return actions


def confirm_safe(t, now=None):
    """User tapped 'I'm safe'. Returns True if contacts had already been alerted (so they must be told it's resolved)."""
    now = now or time.time()
    told = t.contacts_alerted
    t.level, t.reason, t.off_count = 0, None, 0
    t.cooldown_until = now + settings.COOLDOWN_S
    t.pings.clear()
    t.contacts_alerted = t.control_alerted = False
    _log(t, now, "User confirmed safe")
    return told


def sos(t, now=None):
    now = now or time.time()
    actions = []
    if t.level < 2:
        t.level, t.level_since, t.reason = 2, now, "sos"
        _log(t, now, "SOS pressed: contacts alerted")
        if not t.contacts_alerted:
            t.contacts_alerted = True
            actions.append("notify_contacts")
    return actions


def end(t, now=None):
    now = now or time.time()
    told = t.contacts_alerted and t.status == "active"
    t.status = "ended"
    _log(t, now, "Trip ended")
    return told


def state(t, now=None):
    now = now or time.time()
    left = None
    if t.status == "active" and t.level == 1:
        left = max(0, round(settings.CHECKIN_SECONDS - (now - t.level_since)))
    elif t.status == "active" and t.level == 2:
        left = max(0, round(settings.CONTACTS_TO_CONTROL_S - (now - t.level_since)))
    return {"trip_id": t.id, "status": t.status, "level": t.level, "reason": t.reason,
            "seconds_left": left, "deviation_m": t.deviation_m,
            "position": list(t.last_pos) if t.last_pos else None, "events": t.events[-6:]}
