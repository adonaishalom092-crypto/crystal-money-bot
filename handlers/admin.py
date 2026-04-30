import asyncio
import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import db
from config import ADMIN_ID
from keyboards import main_keyboard, manage_channels_keyboard
from utils.states import BroadcastState, AddChannelState, BanState, UnbanState

logger = logging.getLogger(__name__)
BROADCAST_DELAY = 0.05

# État FSM pour la réponse admin
class ReplyState(StatesGroup):
    waiting_reply = State()

# Stocke temporairement l'ID cible de l'admin
_admin_reply_target: dict = {}


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
        wait_msg = await message.answer("⏳ Vérification en cours, patiente quelques secondes…")
        try:
            active_stats = await db.get_active_users_count(message.bot)
        except Exception as e:
            logger.error(f"Erreur get_active_users_count: {e}")
            active_stats = None
        await wait_msg.delete()
        if active_stats:
            await message.answer(
                f"📈 <b>STATS COMPLÈTES</b>\n\n"
                f"👥 Utilisateurs total : <b>{s['users']}</b>\n"
                f"✅ Actifs (dans le canal) : <b>{active_stats['active']}</b>\n"
                f"❌ Inactifs (hors canal) : <b>{active_stats['inactive']}</b>\n"
                f"🚫 Bannis : <b>{active_stats['banned']}</b>\n\n"
                f"💸 Retraits total : <b>{s['total_withdrawals']}</b>\n"
                f"⏳ En attente : <b>{s['pending']}</b>\n"
                f"💰 Balance en circulation : <b>{s['total_balance']} FCFA</b>"
            )
        else:
            await message.answer(
                f"📈 <b>STATS</b>\n\n"
                f"👥 Utilisateurs : {s['users']}\n"
                f"💸 Retraits : {s['total_withdrawals']}\n"
                f"⏳ En attente : {s['pending']}\n"
                f"💰 Balance totale : {s['total_balance']} FCFA"
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
        await status_msg.edit_text(
            f"📢 <b>TERMINÉ</b>\n\n✅ {success} envoyés\n❌ {failed} échecs"
        )

    @dp.message_handler(lambda m: m.text == "📡 Gérer Canaux" and m.from_user.id == ADMIN_ID)
    async def manage_channels(message: types.Message):
        channels = await db.get_channels()
        channels_text = "\n".join([f"• {ch}" for ch in channels]) or "Aucun canal."
        await message.answer(
            f"📡 <b>CANAUX</b>\n\n{channels_text}",
            reply_markup=manage_channels_keyboard(channels)
        )

    @dp.callback_query_handler(lambda c: c.data == "add_channel")
    async def add_channel_start(call: types.CallbackQuery):
        if call.from_user.id != ADMIN_ID:
            return
        await call.message.answer(
            "➕ Envoie le username du canal.\n"
            "Exemple : <code>@moncanal</code>\n\n"
            "Envoie /cancel pour annuler."
        )
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
        await message.answer(
            f"✅ Canal <b>{username}</b> ajouté !"
            if added else
            f"⚠️ <b>{username}</b> existe déjà."
        )

    @dp.callback_query_handler(lambda c: c.data.startswith("del_channel:"))
    async def delete_channel(call: types.CallbackQuery):
        if call.from_user.id != ADMIN_ID:
            return
        username = call.data.split(":", 1)[1]
        await db.delete_channel(username)
        channels = await db.get_channels()
        channels_text = "\n".join([f"• {ch}" for ch in channels]) or "Aucun canal."
        await call.message.edit_text(
            f"🗑 <b>{username}</b> supprimé.\n\n📡 Restants :\n{channels_text}",
            reply_markup=manage_channels_keyboard(channels) if channels else None
        )
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

    @dp.message_handler(commands=["userinfo"])
    async def user_info(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            return
        try:
            parts = message.text.split(" ", 1)
            target_id = int(parts[1])
        except Exception:
            return await message.answer("❌ Format : /userinfo <ID>")
        user = await db.get_user(target_id)
        if not user:
            return await message.answer("❌ Utilisateur introuvable.")
        await message.answer(
            f"👤 <b>PROFIL UTILISATEUR</b>\n\n"
            f"🆔 ID : <code>{target_id}</code>\n"
            f"🌍 Pays : {user['country'] or 'Inconnu'}\n"
            f"🗣 Langue : {user['language'] or 'Inconnue'}\n"
            f"💰 Solde : <b>{user['balance']} FCFA</b>\n"
            f"👥 Parrainages : <b>{user['total_referrals']}</b>\n"
            f"🎁 Bonus réclamés : <b>{user['total_bonus']}</b>\n"
            f"🚫 Banni : {'Oui' if user['is_banned'] else 'Non'}"
        )

    # ------------------------------------------------------------------
    # Réception messages utilisateurs → admin
    # Supporte : texte, vocal, audio, photo, vidéo, document, sticker
    # ------------------------------------------------------------------

    @dp.message_handler(
        lambda m: m.from_user.id != ADMIN_ID,
        content_types=[
            types.ContentType.TEXT,
            types.ContentType.VOICE,
            types.ContentType.AUDIO,
            types.ContentType.PHOTO,
            types.ContentType.VIDEO,
            types.ContentType.DOCUMENT,
            types.ContentType.STICKER,
        ],
        state=None
    )
    async def forward_to_admin(message: types.Message):
        try:
            # En-tête avec bouton répondre
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton(
                f"↩️ Répondre à {message.from_user.first_name}",
                callback_data=f"reply_to:{message.from_user.id}"
            ))

            await message.bot.send_message(
                ADMIN_ID,
                f"📩 <b>Message de {message.from_user.first_name}</b>\n"
                f"👤 ID : <code>{message.from_user.id}</code>\n"
                f"📎 Type : {message.content_type}",
                reply_markup=kb
            )
            # Transférer le message original
            await message.forward(ADMIN_ID)

        except Exception as e:
            logger.error(f"Impossible de transmettre: {e}")

    # ------------------------------------------------------------------
    # Admin clique sur "Répondre" → entre en mode réponse
    # ------------------------------------------------------------------

    @dp.callback_query_handler(lambda c: c.data.startswith("reply_to:"))
    async def reply_to_user_start(call: types.CallbackQuery, state: FSMContext):
        if call.from_user.id != ADMIN_ID:
            return
        target_id = int(call.data.split(":")[1])
        _admin_reply_target[ADMIN_ID] = target_id
        await call.message.answer(
            f"↩️ Tu réponds à l'utilisateur <code>{target_id}</code>\n\n"
            f"Envoie ton message (texte, vocal, photo, vidéo…)\n\n"
            f"Envoie /cancel pour annuler."
        )
        await ReplyState.waiting_reply.set()
        await call.answer()

    # ------------------------------------------------------------------
    # Admin envoie sa réponse (n'importe quel type)
    # ------------------------------------------------------------------

    @dp.message_handler(
        state=ReplyState.waiting_reply,
        content_types=[
            types.ContentType.TEXT,
            types.ContentType.VOICE,
            types.ContentType.AUDIO,
            types.ContentType.PHOTO,
            types.ContentType.VIDEO,
            types.ContentType.DOCUMENT,
            types.ContentType.STICKER,
        ]
    )
    async def reply_to_user_send(message: types.Message, state: FSMContext):
        if message.from_user.id != ADMIN_ID:
            return
        await state.finish()

        target_id = _admin_reply_target.get(ADMIN_ID)
        if not target_id:
            return await message.answer("❌ Cible introuvable. Réessaie.")

        try:
            # Envoyer en-tête à l'utilisateur
            await message.bot.send_message(
                target_id,
                "📨 <b>Message de l'administrateur :</b>"
            )
            # Copier le message (vocal, photo, texte, etc.)
            await message.copy_to(target_id)
            await message.answer("✅ Réponse envoyée.")
        except Exception as e:
            logger.error(f"Impossible de répondre à {target_id}: {e}")
            await message.answer("❌ Impossible d'envoyer. L'utilisateur a peut-être bloqué le bot.")
        finally:
            _admin_reply_target.pop(ADMIN_ID, None)
