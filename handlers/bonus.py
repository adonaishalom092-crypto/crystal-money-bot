import logging
from datetime import datetime
from aiogram import Dispatcher, types

import db
from config import DAILY_BONUS

logger = logging.getLogger(__name__)

def register_bonus(dp: Dispatcher):

    @dp.message_handler(lambda m: m.text == "🎁 Bonus")
    async def bonus(message: types.Message):
        user_id = message.from_user.id
        today = str(datetime.now().date())
        try:
            granted = await db.claim_daily_bonus(user_id, today)
        except Exception as e:
            logger.error(f"Erreur claim_daily_bonus: {e}")
            return await message.answer("❌ Une erreur est survenue. Réessaie plus tard.")
        if not granted:
            return await message.answer("⏳ Tu as déjà réclamé ton bonus aujourd'hui.\nReviens demain 😉")
        bal = await db.get_balance(user_id)
        await message.answer(
            f"🎁 <b>BONUS QUOTIDIEN</b>\n\n"
            f"Félicitations ! Tu as reçu :\n<b>+{DAILY_BONUS} FCFA 💰</b>\n\n"
            f"Solde actuel : <b>{bal} FCFA</b>\n\n"
            f"⏳ Reviens demain pour réclamer encore plus !"
        )
