# Deploy Raahi backend (free) — do these in order, test after each

Repo layout: `women-safety-app/` (frontend, already deployed) + `backend/` (new API) + `render.yaml`.

## 1. Add your model (10 min)
1. In Colab run `import sklearn; print(sklearn.__version__)` and put that version in `backend/requirements.txt`.
2. Download from Colab and put in `backend/models/`:
   `safety_score_model.pkl`, `safety_score_encoder.pkl`, `safety_score_columns.pkl`
3. Run the snippet in `backend/README.md` in Colab, put `safety_score_defaults.json` in `backend/models/` too.
4. Test locally: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000`
   then open http://localhost:8000/api/health — must show `"model_ready": true`.
   (If it shows a load error: `python train.py "<your csv>" models/` rebuilds the files for your Python.)

## 2. Deploy API on Render (free)
1. Push this repo to GitHub (commit the 4 model files; they're small).
2. Render → New → Blueprint → pick the repo (reads `render.yaml`). Free plan.
3. Set env vars: `CORS_ORIGINS` = your deployed frontend URL(s), comma separated; `USER_AGENT` = "RaahiSafetyApp/0.1 (your email)".
4. Open `https://<your-service>.onrender.com/api/health` → `model_ready: true`.
   Free plan sleeps after 15 min idle; first request takes ~1 min (the app pings it on load to hide this).

## 3. Connect the frontend
Set `VITE_API_URL=https://<your-service>.onrender.com` in your frontend host's *build* environment variables,
then rebuild/redeploy. (Without it the app runs in its old mock mode.)

## 4. Free automatic alerts via Telegram (optional)
1. Telegram → @BotFather → /newbot → copy token + username.
2. Render env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET` (any long random string).
3. Register the webhook once:
   `curl "https://api.telegram.org/bot<TOKEN>/setWebhook" -d "url=https://<your-service>.onrender.com/api/telegram/webhook" -d "secret_token=<SECRET>"`
4. In the app: Alerts → add contact → "Link Telegram" → send the link to that person; they open it and press Start.
