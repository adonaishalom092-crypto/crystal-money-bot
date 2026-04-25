import asyncio
import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

import db
from config import ADMIN_ID
from keyboards import main_keyboard, manage_channels_keyboard
from utils.states import BroadcastState, AddChannelState, BanState, UnbanState

logger = logging.getLogger(__name__)
BROADCAST_DELAY = 0.05

def register_admin(dp: Dispatcher):

    @dp.message_handler(lambda m: m.text == "📊 Admin Panel" and m.from_user.id == ADMIN_ID)
    async def admin_panel(message: types.Message):
        s = await db.get_stats()
        await message.answer(
            f"🛠️ <b>ADMIN PANEL</b>\n\n"
            f"👥 Utilisateurs : <b>{s['users']}</b>\n"
            f"⏳ En attente : <b>{s['pending']}</b>\n"
            f"💸 Retraits totaux : <b>{s['total_withdrawals']}</b>\n"
            f"💰 Balance totale : <b>{s['total_balance']} FCFA</b>"
        )

    @dp.message_handler(lambda m: m.text == "📈 Stats" and m.from_user.id == ADMIN_ID)
    async def stats(message: types.Message):
        s = await db.get_stats()
        await message.answer(
            f"📈 <b>STATS</b>\n\n👥 {s['users']} utilisateurs\n"
            f"💸 {s['total_withdrawals']} retraits\n⏳ {s['pending']} en attente\n"
            f"💰 {s['total_balance']} FCFA en circulation"
        )

    @dp.message_handler(lambda m: m.text == "📢 Broadcast" and m.from_user.id == ADMIN_ID)
    async def broadcast_start(message: types.Message):
        await message.answer("📢 Envoie le message à diffuser.\n\nEnvoie /cancel pour annuler.")
        await BroadcastState.message.set()

    @dp.message_handler(state=BroadcastState.message, content_types=types.ContentTypes.ANY)
    async def broadcast_send(message: types.Message, state: FSMContext):
        if message.from_user.id != ADMIN_ID:
            return
        await state.finish()
        user_ids = await db.get_all_user_ids()
        success = failed = 0
        status_msg = await message.answer(f"⏳ Envoi à {len(user_ids)} utilisateurs…")
        for uid in user_ids:
            try:
                await message.copy_to(uid)
                success += 1
            except Exception:
                failed += 1
            await asyncio.sleep(BROADCAST_DELAY)
        await status_msg.edit_text(f"📢 <b>TERMINÉ</b>\n\n✅ {success} envoyés\n❌ {failed} échecs")

    @dp.message_handler(lambda m: m.text == "📡 Gérer Canaux" and m.from_user.id == ADMIN_ID)
    async def manage_channels(message: types.Message):
        channels = await db.get_channels()
        channels_text = "\n".join([f"• {ch}" for ch in channels]) or "Aucun canal."
        await message.answer(f"📡 <b>CANAUX</b>\n\n{channels_text}", reply_markup=manage_channels_keyboard(channels))

    @dp.callback_query_handler(lambda c: c.data == "add_channel")
    async def add_channel_start(call: types.CallbackQuery):
        if call.from_user.id != ADMIN_ID:
            return
        await call.message.answer("➕ Envoie le username du canal.\nExemple : <code>@moncanal</code>\n\nEnvoie /cancel pour annuler.")
        await AddChannelState.username.set()
        await call.answer()

    @dp.message_handler(state=AddChannelState.username)
    async def add_channel_save(message: types.Message, state: FSMContext):
        if message.from_user.id != ADMIN_ID:
            return
        username = message.text.strip()
        await state.finish()
        if not username.startswith("@"):
            return await message.answer("❌ Le username doit commencer par @")
        added = await db.add_channel(username)
        await message.answer(f"✅ Canal <b>{username}</b> ajouté !" if added else f"⚠️ <b>{username}</b> existe déjà.")

    @dp.callback_query_handler(lambda c: c.data.startswith("del_channel:"))
    async def delete_channel(call: types.CallbackQuery):
        if call.from_user.id != ADMIN_ID:
            return
        username = call.data.split(":", 1)[1]
        await db.delete_channel(username)
        channels = await db.get_channels()
        channels_text = "\n".join([f"• {ch}" for ch in channels]) or "Aucun canal."
        await call.message.edit_text(f"🗑 <b>{username}</b> supprimé.\n\n📡 Restants :\n{channels_text}",
            reply_markup=manage_channels_keyboard(channels) if channels else None)
        await call.answer("Supprimé ✅")

    @dp.message_handler(lambda m: m.text == "🔨 Bannir" and m.from_user.id == ADMIN_ID)
    async def ban_start(message: types.Message):
        await message.answer("🔨 Envoie l'ID à bannir.\n\nEnvoie /cancel pour annuler.")
        await BanState.user_id.set()

    @dp.message_handler(state=BanState.user_id)
    async def ban_execute(message: types.Message, state: FSMContext):
        if message.from_user.id != ADMIN_ID:
            return
        await state.finish()
        if not message.text.strip().isdigit():
            return await message.answer("❌ ID invalide.")
        target = int(message.text.strip())
        await db.ban_user(target)
        try:
            await message.bot.send_message(target, "🚫 Tu as été banni de ce bot.")
        except Exception:
            pass
        await message.answer(f"🔨 <code>{target}</code> banni.")

    @dp.message_handler(lambda m: m.text == "✅ Débannir" and m.from_user.id == ADMIN_ID)
    async def unban_start(message: types.Message):
        await message.answer("✅ Envoie l'ID à débannir.\n\nEnvoie /cancel pour annuler.")
        await UnbanState.user_id.set()

    @dp.message_handler(state=UnbanState.user_id)
    async def unban_execute(message: types.Message, state: FSMContext):
        if message.from_user.id != ADMIN_ID:
            return
        await state.finish()
        if not message.text.strip().isdigit():
            return await message.answer("❌ ID invalide.")
        target = int(message.text.strip())
        await db.unban_user(target)
        try:
            await message.bot.send_message(target, "✅ Tu as été débanni !")
        except Exception:
            pass
        await message.answer(f"✅ <code>{target}</code> débanni.")

    @dp.message_handler(lambda m: m.from_user.id != ADMIN_ID, content_types=types.ContentTypes.TEXT, state=None)
    async def forward_to_admin(message: types.Message):
        try:
            await message.bot.send_message(
                ADMIN_ID,
                f"📩 <b>Message utilisateur</b>\n\n👤 ID : <code>{message.from_user.id}</code>\n💬 {message.text}"
            )
        except Exception as e:
            logger.error(f"Impossible de transmettre: {e}")

    @dp.message_handler(commands=["reply"], state=None)
    async def admin_reply(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            return
        try:
            parts = message.text.split(" ", 2)
            await message.bot.send_message(int(parts[1]), parts[2])
            await message.answer("✅ Message envoyé.")
        except Exception:
            await message.answer("❌ Format : /reply <ID> <message>")
