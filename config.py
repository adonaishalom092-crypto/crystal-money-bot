import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"[CONFIG] Variable d'environnement manquante : {key}")
    return value

def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)

# ── Variables obligatoires ──────────────────────────────────────────
API_TOKEN: str = _require("API_TOKEN")
ADMIN_ID: int = int(_require("ADMIN_ID"))

# ── Variables PayGenius ─────────────────────────────────────────────
GENIUSPAY_API_KEY: str = _optional("GENIUSPAY_API_KEY")
GENIUSPAY_WALLET_ID: str = _optional("GENIUSPAY_WALLET_ID")

# ── Constantes du bot ───────────────────────────────────────────────
DAILY_BONUS: int = 50            # FCFA par bonus quotidien
REFERRAL_BONUS: int = 1500       # FCFA par parrainage validé
MIN_WITHDRAW: int = 30000        # Montant minimum de retrait
MIN_REFERRALS: int = 20          # Parrainages requis par retrait
RATE_LIMIT_SECONDS: int = 2      # Délai minimum entre deux actions
