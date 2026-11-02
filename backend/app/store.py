"""Tiny SQLite store: crowd ratings + Telegram link codes.
NOTE: free hosts (Render free) have an ephemeral disk, so this resets on redeploy/restart.
Swap for Supabase/Neon Postgres if you need ratings to be permanent (see README)."""
import secrets
import sqlite3
import threading
import time

from . import settings
from .geo import haversine_m

_lock = threading.Lock()
_conn = None


def _db():
    global _conn
    if _conn is None:
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(settings.DATA_DIR / "raahi.db", check_same_thread=False)
        _conn.executescript(
            """CREATE TABLE IF NOT EXISTS ratings(id INTEGER PRIMARY KEY, lat REAL, lng REAL, rating REAL, ts REAL);
               CREATE TABLE IF NOT EXISTS tg_links(code TEXT PRIMARY KEY, chat_id TEXT, ts REAL);"""
        )
    return _conn


def reset_for_tests():
    global _conn
    _conn = None


def add_rating(lat, lng, rating):
    with _lock:
        _db().execute("INSERT INTO ratings(lat,lng,rating,ts) VALUES(?,?,?,?)", (lat, lng, rating, time.time()))
        _db().commit()


def crowd_rating_near(lat, lng, radius_m=300, min_count=3):
    """Median of nearby user ratings (median resists a single spammy rating); None if too few."""
    d = radius_m / 111000.0
    with _lock:
        rows = _db().execute(
            "SELECT lat,lng,rating FROM ratings WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?",
            (lat - d, lat + d, lng - d * 1.2, lng + d * 1.2),
        ).fetchall()
    vals = sorted(r for la, lo, r in rows if haversine_m(lat, lng, la, lo) <= radius_m)
    if len(vals) < min_count:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def new_link_code():
    code = secrets.token_urlsafe(6).replace("-", "a").replace("_", "b")
    with _lock:
        _db().execute("INSERT INTO tg_links(code,chat_id,ts) VALUES(?,?,?)", (code, None, time.time()))
        _db().commit()
    return code


def set_link(code, chat_id):
    with _lock:
        cur = _db().execute("UPDATE tg_links SET chat_id=? WHERE code=? AND chat_id IS NULL", (str(chat_id), code))
        _db().commit()
        return cur.rowcount > 0


def get_link(code):
    with _lock:
        r = _db().execute("SELECT chat_id FROM tg_links WHERE code=?", (code,)).fetchone()
    return None if r is None else (r[0] or "")
