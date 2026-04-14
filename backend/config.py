"""Application configuration: env vars and shared constants."""

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ---- Secrets / external services ----
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]

# ---- Auth ----
JWT_ALGORITHM = "HS256"
ACCOUNT_REUSE_COOLDOWN_DAYS = 30
VERIFICATION_CODE_EXPIRY_MINUTES = 10
EMAIL_MOCK_MODE = True  # Set to False when Resend is configured

# ---- Binary paths (resolved lazily — `ensure_ffmpeg()` may update them) ----
YT_DLP_PATH = shutil.which("yt-dlp") or "/root/.venv/bin/yt-dlp"
FFMPEG_PATH = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
FFPROBE_PATH = shutil.which("ffprobe") or "/usr/bin/ffprobe"

# ---- Plans & quotas ----
FREE_SCANS_PER_WEEK = 2
PREMIUM_FUP_MONTHLY_CAP = 175
REFERRAL_BONUS_SCANS = 3

PLANS = {
    "premium_monthly": {"amount": 13.99, "currency": "usd", "label": "Premium Monthly", "days": 30},
    "premium_annual": {"amount": 119.00, "currency": "usd", "label": "Premium Annual", "days": 365},
}
