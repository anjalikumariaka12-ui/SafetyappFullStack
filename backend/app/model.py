"""Wraps the notebook's saved sklearn model (GradientBoostingRegressor + OneHotEncoder).

Feature pipeline is identical to the notebook:
  numeric columns (in saved order) + one-hot(road_class, ward_id, time_of_day) -> scipy hstack -> predict
"""
import json
import logging

log = logging.getLogger("raahi.model")

# Used only if safety_score_defaults.json wasn't exported from Colab. Rough, so scores are less trustworthy.
FALLBACK_DEFAULTS = {
    "road_length_km": 0.15, "population_density_per_km2": 7000, "police_distance_km": 5.0,
    "nearest_station_total_cases_2024": 300, "street_lights_per_km": 150, "crowd_safety_rating": 3.0,
    "cctv_coverage_pct": 55, "estimated_emergency_response_min": 15, "traffic_level": 0.5,
    "pedestrian_activity_index": 0.5, "estimated_daily_trips": 800, "reported_safety_incidents_30d": 3,
}
FALLBACK_RANGES = {  # (p05, p95) guesses for normalising factor bars
    "street_lights_per_km": (20, 250), "crowd_safety_rating": (1, 5), "police_distance_km": (0.5, 12),
    "reported_safety_incidents_30d": (0, 15), "cctv_coverage_pct": (10, 90),
}


class SafetyModel:
    def __init__(self, model_dir):
        self.ready = False
        self.error = None
        self.defaults = dict(FALLBACK_DEFAULTS)
        self.ranges = dict(FALLBACK_RANGES)
        self.defaults_from_data = False
        self.sklearn_trained_with = None
        self.model = self.encoder = None
        self.categories = {}
        self.categorical_cols, self.numerical_cols = [], []
        try:
            import joblib
            self.model = joblib.load(model_dir / "safety_score_model.pkl")
            self.encoder = joblib.load(model_dir / "safety_score_encoder.pkl")
            cols = joblib.load(model_dir / "safety_score_columns.pkl")
            self.categorical_cols = list(cols["categorical_cols"])
            self.numerical_cols = list(cols["numerical_cols"])
            self.ready = True
        except FileNotFoundError as e:
            self.error = f"model files not found in {model_dir} ({e.filename})"
        except Exception as e:  # corrupt file, sklearn version mismatch, ...
            self.error = f"{type(e).__name__}: {e}"
        if not self.ready:
            log.warning("Model not loaded: %s", self.error)
            return
        p = model_dir / "safety_score_defaults.json"
        if p.exists():
            d = json.loads(p.read_text())
            self.defaults.update(d.get("medians", {}))
            for k, lo in d.get("p05", {}).items():
                if k in d.get("p95", {}):
                    self.ranges[k] = (lo, d["p95"][k])
            self.sklearn_trained_with = d.get("sklearn")
            self.defaults_from_data = True
        self.categories = {c: list(cats) for c, cats in zip(self.categorical_cols, self.encoder.categories_)}

    # ---- helpers -------------------------------------------------------
    def time_label(self, hour):
        """Map an hour (0-23) to whichever time_of_day labels the encoder was trained on."""
        known = self.categories.get("time_of_day", []) if self.ready else []
        pref = (["night"] if hour >= 21 or hour < 5 else ["morning"] if hour < 12
                else ["afternoon"] if hour < 17 else ["evening", "night", "afternoon"])
        pref = pref + ["night", "afternoon", "morning", "evening"]
        for p in pref:
            if p in known or not known:
                return p
        return known[0]

    def default_road_class(self):
        known = self.categories.get("road_class", []) if self.ready else []
        return "major_road" if "major_road" in known or not known else known[0]

    def norm(self, feature, value):
        """0..1 position of value inside the training p05..p95 range."""
        lo, hi = self.ranges.get(feature, (0, 1))
        return 0.0 if hi == lo else max(0.0, min(1.0, (value - lo) / (hi - lo)))

    def denorm(self, feature, q):
        lo, hi = self.ranges.get(feature, (0, 1))
        return lo + max(0.0, min(1.0, q)) * (hi - lo)

    # ---- inference -----------------------------------------------------
    def predict(self, rows):
        """rows: list of dicts holding every categorical + numerical column. Returns scores 0-100."""
        if not self.ready:
            raise RuntimeError(self.error or "model not loaded")
        import pandas as pd
        from scipy.sparse import hstack
        df = pd.DataFrame(rows)
        missing = [c for c in self.categorical_cols + self.numerical_cols if c not in df.columns]
        if missing:
            raise ValueError(f"missing features: {missing}")
        cat = self.encoder.transform(df[self.categorical_cols])
        num = df[self.numerical_cols].astype(float).values
        X = hstack([num, cat]).tocsr()
        return [float(max(0.0, min(100.0, p))) for p in self.model.predict(X)]


def heuristic_score(f, ranges):
    """Fallback when the trained model isn't deployed yet. NOT the ML model; flagged as such in responses."""
    def n(k, v):
        lo, hi = ranges.get(k, (0, 1))
        return 0.0 if hi == lo else max(0.0, min(1.0, (v - lo) / (hi - lo)))
    good = (0.25 * n("street_lights_per_km", f["street_lights_per_km"])
            + 0.25 * n("crowd_safety_rating", f["crowd_safety_rating"])
            + 0.15 * n("cctv_coverage_pct", f["cctv_coverage_pct"])
            + 0.15 * (1 - n("police_distance_km", f["police_distance_km"]))
            + 0.20 * (1 - n("reported_safety_incidents_30d", f["reported_safety_incidents_30d"])))
    return 25 + 70 * good
