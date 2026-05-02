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

# ── Variables PayGenius (obligatoires si paiement automatique activé)
GENIUSPAY_API_KEY: str = _optional("GENIUSPAY_API_KEY")
GENIUSPAY_WALLET_ID: str = _optional("GENIUSPAY_WALLET_ID")

# ── Constantes du bot ───────────────────────────────────────────────
DAILY_BONUS: int = 100          # FCFA accordés par bonus quotidien
REFERRAL_BONUS: int = 150       # FCFA accordés par parrainage validé
MIN_WITHDRAW: int = 500         # Montant minimum de retrait en FCFA
MIN_REFERRALS: int = 3          # Parrainages minimum requis pour retirer
RATE_LIMIT_SECONDS: int = 2     # Délai minimum entre deux actions (secondes)
