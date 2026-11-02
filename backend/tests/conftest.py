"""Builds a SYNTHETIC training set with the notebook's exact schema, trains with train.py, and points the API at it.
This only proves the plumbing; it says nothing about your real model's accuracy."""
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
TMP = Path(tempfile.mkdtemp())
os.environ["MODEL_DIR"] = str(TMP / "models")
os.environ["DATA_DIR"] = str(TMP / "data")


def synth(n=1500, seed=0):
    r = np.random.default_rng(seed)
    d = pd.DataFrame({
        "road_class": r.choice(["major_road", "link_road", "national_highway", "residential"], n),
        "ward_id": r.choice([f"W{i}" for i in range(1, 68)], n),
        "time_of_day": r.choice(["morning", "afternoon", "evening", "night"], n),
        "road_length_km": r.uniform(0.03, 0.3, n), "population_density_per_km2": r.uniform(2000, 16000, n),
        "police_distance_km": r.uniform(0.5, 12, n), "nearest_station_total_cases_2024": r.choice([231, 711, 833], n),
        "street_lights_per_km": r.uniform(20, 250, n), "crowd_safety_rating": r.uniform(1, 5, n),
        "cctv_coverage_pct": r.uniform(10, 90, n), "estimated_emergency_response_min": r.uniform(5, 30, n),
        "traffic_level": r.uniform(0, 1, n), "pedestrian_activity_index": r.uniform(0, 1, n),
        "estimated_daily_trips": r.integers(100, 1500, n), "reported_safety_incidents_30d": r.integers(0, 16, n),
    })
    d["observed_safety_score_0_100"] = (60 + 0.08 * d.street_lights_per_km + 5 * d.crowd_safety_rating
        - 2.2 * d.reported_safety_incidents_30d - 1.2 * d.police_distance_km - 12 * (d.time_of_day == "night")
        + r.normal(0, 4, n)).clip(0, 100)
    return d


from train import train  # noqa: E402

train(synth(), TMP / "models", verbose=False)
