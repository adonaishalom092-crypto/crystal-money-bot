import logging
import re
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

import db
from config import ADMIN_ID, MIN_WITHDRAW, MIN_REFERRALS
from keyboards import confirm_withdraw_keyboard, admin_withdraw_keyboard, main_keyboard
from utils.states import WithdrawState

logger = logging.getLogger(__name__)
_processing_wids: set = set()

def flouter_numero(numero: str) -> str:
    """
    Floute le numéro en gardant les 3 premiers 
    et les 2 derniers caractères visibles.
    Exemple : +225 07 12 34 56 78 → +22 ** 78
    """
    numero = numero.strip()
    if len(numero) <= 5:
        return "***"
    return numero[:3] + " ** " + numero[-2:]

def register_withdraw(dp: Dispatcher):

    @dp.message_handler(lambda m: m.text == "💸 Retrait")
    async def retrait_start(message: types.Message):
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        bal = await db.get_balance(user_id)
        total_referrals = user["total_referrals"] if user else 0
        if bal < MIN_WITHDRAW:
            return await message.answer(f"❌ Solde insuffisant.\nMinimum : <b>{MIN_WITHDRAW} FCFA</b>\nTon solde : <b>{bal} FCFA</b>")
        if total_referrals < MIN_REFERRALS:
            return await message.answer(f"❌ Tu dois parrainer au moins <b>{MIN_REFERRALS} personnes</b>.\n📊 Actuels : <b>{total_referrals}/{MIN_REFERRALS}</b>")
        pending = await db.count_pending_withdrawals(user_id)
        if pending > 0:
            return await message.answer("⏳ Tu as déjà une demande en attente.")
        await message.answer("💳 Quel est ton mode de paiement ?\nExemple : <i>Mobile Money, Wave…</i>\n\nEnvoie /cancel pour annuler.")
        await WithdrawState.method.set()

    @dp.message_handler(state=WithdrawState.method)
    async def get_method(message: types.Message, state: FSMContext):
        method = message.text.strip()
        if len(method) > 50:
            return await message.answer("❌ Méthode trop longue (max 50 caractères).")
        await state.update_data(method=method)
        await message.answer("📱 Ton numéro avec indicatif.\nExemple : <code>+225 07 XX XX XX XX</code>")
        await WithdrawState.next()

    @dp.message_handler(state=WithdrawState.number)
    async def get_number(message: types.Message, state: FSMContext):
        number = message.text.strip()
        if not re.match(r"^[\d\s\+\-]{6,20}$", number):
            return await message.answer("❌ Numéro invalide.\nExemple : <code>+225 07 12 34 56 78</code>")
        await state.update_data(number=number)
        await message.answer("👤 Nom complet du bénéficiaire ?")
        await WithdrawState.next()

    @dp.message_handler(state=WithdrawState.name)
    async def get_name(message: types.Message, state: FSMContext):
        name = message.text.strip()
        if len(name) < 2 or len(name) > 60:
            return await message.answer("❌ Nom invalide (2 à 60 caractères).")
        data = await state.get_data()
        user_id = message.from_user.id
        bal = await db.get_balance(user_id)
        if bal < MIN_WITHDRAW:
            await state.finish()
            return await message.answer("❌ Solde insuffisant. Retrait annulé.")
        await state.update_data(name=name)
        await message.answer(
            f"📋 <b>RÉCAPITULATIF</b>\n\n"
            f"💰 Montant : <b>{bal} FCFA</b>\n"
            f"💳 Méthode : <b>{data['method']}</b>\n"
            f"📱 Numéro : <b>{data['number']}</b>\n"
            f"👤 Nom : <b>{name}</b>\n\n"
            f"Confirmes-tu ?",
            reply_markup=confirm_withdraw_keyboard(bal),
        )
        await WithdrawState.next()

    @dp.callback_query_handler(lambda c: c.data.startswith("confirm_wd:"), state=WithdrawState.confirm)
    async def confirm_withdraw(call: types.CallbackQuery, state: FSMContext):
        user_id = call.from_user.id
        data = await state.get_data()
        await state.finish()
        bal = await db.get_balance(user_id)
        if bal < MIN_WITHDRAW:
            return await call.message.answer("❌ Solde insuffisant. Retrait annulé.")
        try:
            wid = await db.create_withdrawal(user_id=user_id, amount=bal, method=data["method"], number=data["number"], name=data["name"])
        except Exception as e:
            logger.error(f"Erreur create_withdrawal: {e}")
            return await call.message.answer("❌ Erreur technique. Réessaie plus tard.")
        try:
            await call.bot.send_message(
                ADMIN_ID,
                f"📥 <b>NOUVEAU RETRAIT #{wid}</b>\n\n"
                f"👤 ID : <code>{user_id}</code>\n💰 Montant : <b>{bal} FCFA</b>\n"
                f"💳 Méthode : {data['method']}\n📱 Numéro : {data['number']}\n👤 Nom : {data['name']}",
                reply_markup=admin_withdraw_keyboard(wid),
            )
        except Exception as e:
            logger.error(f"Impossible de notifier l'admin: {e}")
        await call.message.answer("⏳ Demande envoyée. L'admin la traitera bientôt.")
        await call.answer()

    @dp.callback_query_handler(lambda c: c.data == "cancel_wd", state=WithdrawState.confirm)
    async def cancel_withdraw(call: types.CallbackQuery, state: FSMContext):
        await state.finish()
        await call.message.answer("❌ Retrait annulé.", reply_markup=main_keyboard(call.from_user.id))
        await call.answer()

    @dp.callback_query_handler(lambda c: c.data.startswith("wd_paid:"))
    async def wd_paid(call: types.CallbackQuery):
        if call.from_user.id != ADMIN_ID:
            return await call.answer("🚫 Réservé à l'admin.", show_alert=True)
        wid = int(call.data.split(":")[1])
        if wid in _processing_wids:
            return await call.answer("⏳ Déjà en cours.", show_alert=True)
        _processing_wids.add(wid)
        try:
            row = await db.get_withdrawal(wid)
            if not row or row["status"] != "pending":
                return await call.answer(f"⚠️ Statut : {row['status'] if row else 'introuvable'}", show_alert=True)
            await db.pay_withdrawal(wid)
            try:
                await call.bot.send_message(row["user_id"], "✅ Ton retrait a été validé et payé 💰")
            except Exception:
                pass
            await call.bot.send_message(
    "@adonaimoneychannel",
    f"💸 <b>RETRAIT EFFECTUÉ ✅</b>\n\n"
    f"🎉 Un membre vient de recevoir son paiement !\n\n"
    f"💰 Montant : <b>{row['amount']} FCFA</b>\n"
    f"💳 Méthode : <b>{row['method']}</b>\n"
    f"📱 Numéro : <b>{numero_floute}</b>\n"
    f"🕐 Statut : <b>Payé ✅</b>\n\n"
    f"━━━━━━━━━━━━━━━\n"
    f"👉 Toi aussi tu peux gagner !\n"
    f"Rejoins : @adonaimoneychannel"
)

    @dp.callback_query_handler(lambda c: c.data.startswith("wd_refused:"))
    async def wd_refused(call: types.CallbackQuery):
        if call.from_user.id != ADMIN_ID:
            return await call.answer("🚫 Réservé à l'admin.", show_alert=True)
        wid = int(call.data.split(":")[1])
        if wid in _processing_wids:
            return await call.answer("⏳ Déjà en cours.", show_alert=True)
        _processing_wids.add(wid)
        try:
            success = await db.refuse_withdrawal(wid)
            if not success:
                return await call.answer("⚠️ Déjà traité ou introuvable.", show_alert=True)
            row = await db.get_withdrawal(wid)
            try:
                await call.bot.send_message(row["user_id"], "❌ Retrait refusé. Ton solde a été recrédité.")
            except Exception:
                pass
            await call.message.edit_text(call.message.text + "\n\n❌ <b>REFUSÉ</b>", reply_markup=None)
            await call.answer("Refusé ✅")
        finally:
            _processing_wids.discard(wid)
