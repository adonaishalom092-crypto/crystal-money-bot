import logging
from aiogram import Dispatcher, types

import db
from config import REFERRAL_BONUS, MIN_REFERRALS, MIN_WITHDRAW

logger = logging.getLogger(__name__)

HELP_TEXT = f"""
❓ <b>AIDE — ADONAÏ MONEY</b>

<b>🎁 Bonus</b> — Réclame 100 FCFA chaque jour.
<b>👥 Parrainage</b> — Gagne <b>{REFERRAL_BONUS} FCFA</b> par filleul.
<b>💰 Solde</b> — Consulte ton solde.
<b>💸 Retrait</b> — Retire (min. {MIN_WITHDRAW} FCFA, {MIN_REFERRALS} parrainages requis).
<b>📜 Historique</b> — Tes dernières demandes de retrait.
<b>/cancel</b> — Annule l'action en cours.
"""

def register_user(dp: Dispatcher):

    @dp.message_handler(lambda m: m.text == "👥 Parrainage")
    async def referral(message: types.Message):
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        bot_info = await message.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={user_id}"
        referrals = user["total_referrals"] if user else 0
        await message.answer(
            f"👥 <b>TON LIEN D'AFFILIATION</b>\n\n"
            f"🔗 {link}\n\n"
            f"📊 Parrainages validés : <b>{referrals}</b>\n"
            f"💰 Gain par parrainage : <b>{REFERRAL_BONUS} FCFA</b>"
        )

    @dp.message_handler(lambda m: m.text == "💰 Solde")
    async def solde(message: types.Message):
        bal = await db.get_balance(message.from_user.id)
        await message.answer(f"💰 <b>TON SOLDE</b> : {bal} FCFA")

    @dp.message_handler(lambda m: m.text == "❓ Aide")
    async def aide(message: types.Message):
        await message.answer(HELP_TEXT)

    @dp.message_handler(lambda m: m.text == "📜 Historique")
    async def history(message: types.Message):
        rows = await db.get_user_withdrawals(message.from_user.id)
        if not rows:
            return await message.answer("📜 Aucun historique de retrait.")
        STATUS_EMOJI = {"pending": "⏳", "paid": "✅", "refused": "❌"}
        lines = [f"{STATUS_EMOJI.get(r['status'], '❓')} {r['amount']} FCFA — {r['method']} — {r['status']}" for r in rows]
        text = "📜 <b>HISTORIQUE DES RETRAITS</b>\n\n" + "\n".join(lines)
        if len(text) > 4000:
            text = text[:4000] + "\n…(tronqué)"
        await message.answer(text)
