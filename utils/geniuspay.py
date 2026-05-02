import aiohttp
import logging
import uuid

logger = logging.getLogger(__name__)

BASE_URL = "https://pay.genius.ci/api/v1/merchant"

# Mapping méthode utilisateur → provider PayGenius
PROVIDER_MAP = {
    "wave": "wave",
    "orange money": "orange_money",
    "orange": "orange_money",
    "mtn": "mtn",
    "mtn momo": "mtn",
    "momo": "mtn",
    "moov": "moov",
    "moov money": "moov",
}

def detect_provider(method: str) -> str:
    """
    Détecte automatiquement le provider PayGenius
    depuis la méthode saisie par l'utilisateur.
    """
    method_lower = method.lower().strip()
    for key, provider in PROVIDER_MAP.items():
        if key in method_lower:
            return provider
    return "mtn"  # défaut si non reconnu


async def send_payout(
    api_key: str,
    wallet_id: str,
    recipient_name: str,
    recipient_phone: str,
    amount: int,
    provider: str,
    description: str = "Retrait ADONAI_MONEY"
) -> dict:
    """
    Envoie un payout via PayGenius.
    Retourne le dict de réponse PayGenius.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "wallet_id": wallet_id,
        "recipient": {
            "name": recipient_name,
            "phone": recipient_phone,
        },
        "destination": {
            "type": "mobile_money",
            "provider": provider,
            "account": recipient_phone,
        },
        "amount": amount,
        "currency": "XOF",
        "description": description,
        "idempotency_key": str(uuid.uuid4()),
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/payouts",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                logger.info(f"PayGenius response [{resp.status}]: {data}")
                return {"status_code": resp.status, "data": data}

    except Exception as e:
        logger.error(f"Erreur PayGenius send_payout: {e}")
        return {"status_code": 500, "data": {"message": str(e)}}


async def get_payout_status(api_key: str, reference: str) -> dict:
    """
    Vérifie le statut d'un payout PayGenius.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/payouts/{reference}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()
                return {"status_code": resp.status, "data": data}
    except Exception as e:
        logger.error(f"Erreur PayGenius get_payout_status: {e}")
        return {"status_code": 500, "data": {"message": str(e)}}
