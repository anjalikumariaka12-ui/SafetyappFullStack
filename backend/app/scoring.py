"""Route safety scoring.

For each candidate route:
  1. resample the polyline every STEP_M metres
  2. build one feature row per sample point (training medians  <-  route profile  <-  geo CSV  <-  crowd ratings)
  3. predict a safety score per sample with the trained model
  4. route score = 0.75 * mean + 0.25 * worst sample   (one dark stretch shouldn't be averaged away)
"""
import numpy as np

from . import store
from .geo import resample
from .model import heuristic_score

STEP_M = 200


class GeoFeatureProvider:
    """Optional lookup table data/geo_features.csv: lat,lng + any model feature columns.
    The training CSV has no coordinates, so this is where you attach real per-road features to map points."""

    def __init__(self, path):
        self.n = 0
        self.cols = []
        if not path.exists():
            return
        import pandas as pd
        df = pd.read_csv(path)
        if not {"lat", "lng"} <= set(df.columns) or df.empty:
            return
        self.df = df.reset_index(drop=True)
        self.lat = df["lat"].to_numpy(float)
        self.lng = df["lng"].to_numpy(float)
        self.cols = [c for c in df.columns if c not in ("lat", "lng")]
        self.n = len(df)

    def lookup(self, lat, lng, max_m=300):
        if not self.n:
            return None
        dy = (self.lat - lat) * 111000.0
        dx = (self.lng - lng) * 111000.0 * np.cos(np.radians(lat))
        d = np.hypot(dx, dy)
        i = int(d.argmin())
        if d[i] > max_m:
            return None
        row = self.df.iloc[i]
        return {c: row[c] for c in self.cols if not (isinstance(row[c], float) and np.isnan(row[c]))}


def profile_to_features(profile, model):
    """0..1 'quality' per factor -> raw feature values inside the model's training range."""
    out = {}
    if "lighting" in profile: out["street_lights_per_km"] = model.denorm("street_lights_per_km", profile["lighting"])
    if "crowd" in profile: out["crowd_safety_rating"] = model.denorm("crowd_safety_rating", profile["crowd"])
    if "police" in profile: out["police_distance_km"] = model.denorm("police_distance_km", 1 - profile["police"])
    if "incidents" in profile: out["reported_safety_incidents_30d"] = model.denorm("reported_safety_incidents_30d", profile["incidents"])
    if "cctv" in profile: out["cctv_coverage_pct"] = model.denorm("cctv_coverage_pct", profile["cctv"])
    return out


def score_route(route, hour, model, provider):
    samples = resample(route["path"], STEP_M)
    label = model.time_label(hour)
    rows, hits, crowd_hits = [], 0, 0
    prof = profile_to_features(route["profile"], model) if route.get("profile") else {}
    for lat, lng in samples:
        f = dict(model.defaults)
        f.update(prof)
        g = provider.lookup(lat, lng) if provider else None
        if g:
            f.update(g)
            hits += 1
        cr = store.crowd_rating_near(lat, lng)
        if cr is not None:  # user rating 1..5 -> feature range
            f["crowd_safety_rating"] = model.denorm("crowd_safety_rating", (cr - 1) / 4)
            crowd_hits += 1
        f.setdefault("road_class", model.default_road_class())
        f.setdefault("ward_id", "UNKNOWN")  # unknown ward -> all-zero one-hot (encoder ignores unknowns)
        f["time_of_day"] = label
        if not (g and "road_length_km" in g):
            f["road_length_km"] = STEP_M / 1000
        rows.append(f)

    if model.ready:
        scores, engine = model.predict(rows), "model"
    else:
        scores, engine = [heuristic_score(r, model.ranges) for r in rows], "heuristic"

    mean, worst = float(np.mean(scores)), float(np.min(scores))
    score = round(0.75 * mean + 0.25 * worst)
    n = lambda k: float(np.mean([model.norm(k, r[k]) for r in rows]))
    factors = [
        {"label": "Street lighting", "value": round(n("street_lights_per_km"), 2)},
        {"label": "Crowd safety rating", "value": round(n("crowd_safety_rating"), 2)},
        {"label": "Police proximity", "value": round(1 - n("police_distance_km"), 2)},
        {"label": "Historical incident density", "value": round(n("reported_safety_incidents_30d"), 2)},
    ]
    good = [(f["value"] if f["label"] != "Historical incident density" else 1 - f["value"], f["label"]) for f in factors]
    weak, strong = min(good), max(good)
    wi = int(np.argmin(scores))
    note = f"Strongest factor: {strong[1].lower()}. Lowest-rated: {weak[1].lower()}. "
    note += (f"Weakest stretch is about {wi * STEP_M / 1000:.1f} km in (score {round(scores[wi])})."
             if scores[wi] < 65 else "No notably weak stretch found.")
    coverage = hits / len(samples) if samples else 0
    if engine == "heuristic":
        confidence = "heuristic"
    elif coverage == 0 and not route.get("profile") and crowd_hits == 0:
        confidence = "low"  # only training-median features: routes can't be told apart yet
    else:
        confidence = "ok"
    return {
        "id": route["id"], "name": route["name"], "score": score, "distanceKm": route["distanceKm"],
        "minutes": route["minutes"], "path": route["path"], "factors": factors, "note": note,
        "risk": [[round(a, 5), round(b, 5), round(s)] for (a, b), s in zip(samples, scores)],
        "engine": engine, "confidence": confidence, "coverage": round(coverage, 2),
    }


def rank_routes(routes):
    routes = sorted(routes, key=lambda r: -r["score"])
    best = routes[0]
    for i, r in enumerate(routes):
        if i == 0:
            r["tag"] = "Recommended"
        elif r["minutes"] < best["minutes"] - 2:
            r["tag"] = "Faster, less safe"
        elif r["minutes"] > best["minutes"] + 2:
            r["tag"] = "Longer, moderate"
        else:
            r["tag"] = "Alternative"
    return routes
