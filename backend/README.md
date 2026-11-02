# Raahi API (FastAPI)

Serves your trained safety model, ranks routes, monitors live trips and escalates alerts.
Interactive docs: `/docs` once running.

## Put your model in
Copy these 3 files from Colab into `backend/models/`:
`safety_score_model.pkl`, `safety_score_encoder.pkl`, `safety_score_columns.pkl`

Also run this **once in the Colab notebook** (after the cell that builds `X`/`numerical_cols`) and copy the result too.
It gives the API your training medians/ranges, so factor bars and unknown values use real numbers:
```python
import json, sklearn
n = X[numerical_cols]
json.dump({"sklearn": sklearn.__version__, "medians": n.median().to_dict(),
           "p05": n.quantile(.05).to_dict(), "p95": n.quantile(.95).to_dict()},
          open("safety_score_defaults.json", "w"), indent=2)
print(sklearn.__version__)   # <- put this version in requirements.txt
```
Version mismatch / can't load? Retrain on the server instead: `python train.py "your_training.csv" models/`

## Run locally
```bash
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest
python -m pytest -q tests          # 17 tests, uses a synthetic model (plumbing only)
uvicorn app.main:app --reload --port 8000
curl localhost:8000/api/health     # "model_ready": true  <- confirms your .pkl loaded
```

## Endpoints
| | |
|---|---|
| `GET /api/health` | model loaded? channels configured? |
| `POST /api/score` | raw model: rows with the 15 training features -> scores |
| `POST /api/routes/analyze` | origin + destination -> ranked routes with scores, factors, per-point risk |
| `POST /api/trips` / `/location` / `/checkin` / `/sos` / `/end` | live trip + escalation (token in `X-Trip-Token`) |
| `POST /api/ratings` | crowd rating (1-5) at a point; 3+ nearby ratings override `crowd_safety_rating` |
| `POST /api/telegram/link`, `GET /api/telegram/link/{code}`, `POST /api/telegram/webhook` | link a contact's Telegram |
