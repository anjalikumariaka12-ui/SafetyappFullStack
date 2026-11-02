"""All config comes from environment variables so nothing secret lives in git."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _csv(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


def _f(name, default):
    return float(os.getenv(name, default))


MODEL_DIR = Path(os.getenv("MODEL_DIR", ROOT / "models"))
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))

# CORS: put your deployed frontend origin(s) here, comma separated
CORS_ORIGINS = _csv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

# Free map services (public servers: fine for a demo, host your own for real traffic)
OSRM_BASE = os.getenv("OSRM_BASE", "https://router.project-osrm.org")
OSRM_FOOT_BASE = os.getenv("OSRM_FOOT_BASE", "https://routing.openstreetmap.de/routed-foot")
NOMINATIM_BASE = os.getenv("NOMINATIM_BASE", "https://nominatim.openstreetmap.org")
USER_AGENT = os.getenv("USER_AGENT", "RaahiSafetyApp/0.1 (set USER_AGENT env with your email)")

# Alert channels (all optional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")
TWILIO_CALL_PRIMARY = os.getenv("TWILIO_CALL_PRIMARY", "0") == "1"
CONTROL_ROOM_WEBHOOK_URL = os.getenv("CONTROL_ROOM_WEBHOOK_URL", "")

# Trip-monitoring thresholds (tune after real-world testing)
DEVIATION_M_CAB = _f("DEVIATION_M_CAB", 150)
DEVIATION_M_FOOT = _f("DEVIATION_M_FOOT", 80)
DEVIATION_PINGS = int(_f("DEVIATION_PINGS", 3))      # consecutive off-route pings
STALL_SECONDS = _f("STALL_SECONDS", 120)
STALL_SECONDS_LOW_SAFETY = _f("STALL_SECONDS_LOW_SAFETY", 60)
STALL_RADIUS_M = _f("STALL_RADIUS_M", 30)
LOW_SAFETY_SCORE = _f("LOW_SAFETY_SCORE", 55)
SIGNAL_LOST_S = _f("SIGNAL_LOST_S", 180)
CHECKIN_SECONDS = _f("CHECKIN_SECONDS", 30)
CONTACTS_TO_CONTROL_S = _f("CONTACTS_TO_CONTROL_S", 60)
ARRIVAL_M = _f("ARRIVAL_M", 100)
COOLDOWN_S = _f("COOLDOWN_S", 90)                    # quiet period after "I'm safe"
MIN_ACCURACY_M = _f("MIN_ACCURACY_M", 100)           # ignore worse GPS fixes for deviation
TRIP_TTL_S = _f("TRIP_TTL_S", 6 * 3600)              # trips are purged after this
