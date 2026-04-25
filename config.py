import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"[CONFIG] Variable d'environnement manquante : {key}")
    return value

API_TOKEN: str = _require("API_TOKEN")
ADMIN_ID: int = int(_require("ADMIN_ID"))

DAILY_BONUS: int = 100
REFERRAL_BONUS: int = 150
MIN_WITHDRAW: int = 500
MIN_REFERRALS: int = 3
RATE_LIMIT_SECONDS: int = 2
