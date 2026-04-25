import time
import logging
from aiogram import Bot, types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler

import db
from config import RATE_LIMIT_SECONDS
from keyboards import channel_keyboard

logger = logging.getLogger(__name__)
_last_action: dict = {}

class MainMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot):
        self.bot = bot
        super().__init__()

    async def on_pre_process_message(self, message: types.Message, data: dict):
        user_id = message.from_user.id
        command = message.get_command()
        if command == "/start":
            return
        await self._check_ban(user_id, message)
        await self._check_rate_limit(user_id, message)
        if command == "/cancel":
            return
        await self._check_channels(user_id, message)

    async def on_pre_process_callback_query(self, call: types.CallbackQuery, data: dict):
        user_id = call.from_user.id
        if call.data == "check_channel":
            return
        await self._check_ban_callback(user_id, call)
        await self._check_rate_limit_callback(user_id, call)
        await self._check_channels_callback(user_id, call)

    async def _check_ban(self, user_id, message):
        if await db.is_banned(user_id):
            await message.answer("🚫 Tu as été banni de ce bot.")
            raise CancelHandler()

    async def _check_ban_callback(self, user_id, call):
        if await db.is_banned(user_id):
            await call.answer("🚫 Tu as été banni.", show_alert=True)
            raise CancelHandler()

    async def _check_rate_limit(self, user_id, message):
        now = time.monotonic()
        if now - _last_action.get(user_id, 0) < RATE_LIMIT_SECONDS:
            await message.answer("⏳ Doucement ! Attends un instant.")
            raise CancelHandler()
        _last_action[user_id] = now

    async def _check_rate_limit_callback(self, user_id, call):
        now = time.monotonic()
        if now - _last_action.get(user_id, 0) < RATE_LIMIT_SECONDS:
            await call.answer("⏳ Trop rapide !", show_alert=True)
            raise CancelHandler()
        _last_action[user_id] = now

    async def _check_channels(self, user_id, message):
        channels = await db.get_channels()
        if not await _user_in_all_channels(self.bot, user_id, channels):
            channels_text = "\n".join([f"👉 {ch}" for ch in channels])
            await message.answer(
                f"🚫 Rejoins tous les canaux pour utiliser le bot.\n\n{channels_text}",
                reply_markup=channel_keyboard(channels),
            )
            raise CancelHandler()

    async def _check_channels_callback(self, user_id, call):
        channels = await db.get_channels()
        if not await _user_in_all_channels(self.bot, user_id, channels):
            await call.answer("🚫 Rejoins tous les canaux d'abord !", show_alert=True)
            raise CancelHandler()

async def _user_in_all_channels(bot: Bot, user_id: int, channels: list) -> bool:
    try:
        for channel in channels:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        return True
    except Exception as e:
        logger.warning(f"Erreur get_chat_member (user={user_id}): {e}")
        return False
