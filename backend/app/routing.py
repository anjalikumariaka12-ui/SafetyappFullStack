"""Free routing + geocoding (OSRM + Nominatim), with demo-route fallback so the app never dead-ends."""
import logging

import httpx

from . import settings
from .geo import polyline_length_m, resample

log = logging.getLogger("raahi.routing")
_geo_cache = {}
HEADERS = {"User-Agent": settings.USER_AGENT}
BBOX = "85.70,20.15,86.00,20.45"  # Bhubaneswar viewbox: left,top... (biases results, not a hard limit)


async def geocode(q, client=None):
    key = q.strip().lower()
    if key in _geo_cache:
        return _geo_cache[key]
    own = client is None
    client = client or httpx.AsyncClient(timeout=8)
    try:
        r = await client.get(
            f"{settings.NOMINATIM_BASE}/search",
            params={"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "in",
                    "viewbox": "85.70,20.45,86.00,20.15"},
            headers=HEADERS,
        )
        r.raise_for_status()
        data = r.json()
        res = {"label": data[0]["display_name"], "lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])} if data else None
    except Exception as e:
        log.warning("geocode failed: %s", e)
        return None
    finally:
        if own:
            await client.aclose()
    if res:
        _geo_cache[key] = res
    return res


def _thin(path, max_pts=300):
    L = polyline_length_m(path)
    return path if len(path) <= max_pts else resample(path, max(30, L / max_pts))


async def osrm_routes(o, d, mode, client=None):
    base = settings.OSRM_FOOT_BASE if mode == "walk" else settings.OSRM_BASE
    profile = "foot" if mode == "walk" else "driving"
    url = f"{base}/route/v1/{profile}/{o['lng']},{o['lat']};{d['lng']},{d['lat']}"
    own = client is None
    client = client or httpx.AsyncClient(timeout=12)
    try:
        r = await client.get(url, params={"alternatives": "true", "overview": "full", "geometries": "geojson"}, headers=HEADERS)
        r.raise_for_status()
        js = r.json()
    except Exception as e:
        log.warning("osrm failed: %s", e)
        return None
    finally:
        if own:
            await client.aclose()
    if js.get("code") != "Ok":
        return None
    out = []
    for i, rt in enumerate(js["routes"][:3]):
        path = [[lat, lng] for lng, lat in rt["geometry"]["coordinates"]]
        summary = (rt["legs"][0].get("summary") or "").strip()
        out.append({
            "id": f"r{i + 1}", "name": f"Via {summary}" if summary else f"Route {i + 1}",
            "path": _thin(path), "distanceKm": round(rt["distance"] / 1000, 1),
            "minutes": max(1, round(rt["duration"] / 60)), "profile": None,
        })
    return out or None


# Demo routes (same geometry as the frontend's mock data). `profile` = 0..1 quality of each factor,
# mapped into the model's real feature ranges, so the REAL model still produces the scores.
DEMO_ROUTES = [
    {"id": "r1", "name": "Via Patia Main Road", "distanceKm": 6.4, "minutes": 19,
     "path": [[20.3553, 85.8189], [20.3488, 85.8241], [20.3402, 85.8272], [20.3299, 85.8302], [20.3196, 85.8298], [20.2961, 85.8245]],
     "profile": {"lighting": 0.9, "crowd": 0.85, "police": 0.82, "incidents": 0.15, "cctv": 0.8}},
    {"id": "r2", "name": "Via Infocity Shortcut", "distanceKm": 5.1, "minutes": 14,
     "path": [[20.3553, 85.8189], [20.3517, 85.8286], [20.3411, 85.8354], [20.325, 85.8331], [20.2961, 85.8245]],
     "profile": {"lighting": 0.45, "crowd": 0.4, "police": 0.3, "incidents": 0.58, "cctv": 0.35}},
    {"id": "r3", "name": "Via NH16 Bypass", "distanceKm": 8.2, "minutes": 24,
     "path": [[20.3553, 85.8189], [20.3612, 85.8298], [20.3487, 85.8421], [20.3204, 85.8402], [20.2961, 85.8245]],
     "profile": {"lighting": 0.7, "crowd": 0.62, "police": 0.55, "incidents": 0.32, "cctv": 0.55}},
]
