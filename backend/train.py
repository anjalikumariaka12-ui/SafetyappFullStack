"""Re-creates the notebook's final model (GradientBoostingRegressor) from your training CSV and writes the
files the API loads. Run this on the same Python/sklearn the API will use, so the .pkl files always match:

    python train.py "Bhubaneswar_Women_Safety_ML_TRAINING (2).csv" models/
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy.sparse import hstack
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL = ["road_class", "ward_id", "time_of_day"]
FEATURES = CATEGORICAL + [
    "road_length_km", "population_density_per_km2", "police_distance_km", "nearest_station_total_cases_2024",
    "street_lights_per_km", "crowd_safety_rating", "cctv_coverage_pct", "estimated_emergency_response_min",
    "traffic_level", "pedestrian_activity_index", "estimated_daily_trips", "reported_safety_incidents_30d",
]
TARGET = "observed_safety_score_0_100"


def train(df, out_dir, verbose=True):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    X, y = df[FEATURES], df[TARGET]
    numerical = [c for c in X.columns if c not in CATEGORICAL]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    enc = OneHotEncoder(handle_unknown="ignore")
    Xtr_f = hstack([Xtr[numerical].values, enc.fit_transform(Xtr[CATEGORICAL])])
    Xte_f = hstack([Xte[numerical].values, enc.transform(Xte[CATEGORICAL])])
    gb = GradientBoostingRegressor(n_estimators=300, max_depth=5, learning_rate=0.05, random_state=42)
    gb.fit(Xtr_f, ytr)
    pred = gb.predict(Xte_f)
    if verbose:
        print(f"MAE {mean_absolute_error(yte, pred):.2f}  R2 {r2_score(yte, pred):.3f}  (notebook: MAE 9.35, R2 0.700)")
    joblib.dump(gb, out_dir / "safety_score_model.pkl")
    joblib.dump(enc, out_dir / "safety_score_encoder.pkl")
    joblib.dump({"categorical_cols": CATEGORICAL, "numerical_cols": numerical}, out_dir / "safety_score_columns.pkl")
    num = df[numerical]
    (out_dir / "safety_score_defaults.json").write_text(json.dumps({
        "sklearn": sklearn.__version__,
        "medians": num.median().to_dict(),
        "p05": num.quantile(0.05).to_dict(),
        "p95": num.quantile(0.95).to_dict(),
    }, indent=2))
    return gb


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    train(pd.read_csv(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "models")
