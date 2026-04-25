import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

import db
from keyboards import main_keyboard, channel_keyboard

logger = logging.getLogger(__name__)

WELCOME_TEXT = """
<b>Cher(e) {name},</b>

<b>Bienvenue sur l'espace de gain 🗽ADONAÏ_MONEY🗽</b>

Pour bénéficier des services du bot, rejoins le canal officiel :

<b>👉 @adonaimoneychannel</b>

Clique sur <b>Vérifier ✅</b> après avoir rejoint.
"""

def register_start(dp: Dispatcher):

    @dp.message_handler(commands=["start"], state="*")
    async def cmd_start(message: types.Message, state: FSMContext):
        await state.finish()
        user_id = message.from_user.id
        args = message.get_args()
        referrer_id = int(args) if args.isdigit() else None
        await db.get_or_create_user(user_id, referrer_id=referrer_id, language=message.from_user.language_code)
        channels = await db.get_channels()
        await message.answer(WELCOME_TEXT.format(name=message.from_user.first_name), reply_markup=channel_keyboard(channels))

    @dp.message_handler(commands=["cancel"], state="*")
    async def cmd_cancel(message: types.Message, state: FSMContext):
        current = await state.get_state()
        if current:
            await state.finish()
            await message.answer("❌ Action annulée.", reply_markup=main_keyboard(message.from_user.id))
        else:
            await message.answer("Rien à annuler.")

    @dp.callback_query_handler(lambda c: c.data == "check_channel")
    async def check_channel(call: types.CallbackQuery):
        user_id = call.from_user.id
        channels = await db.get_channels()
        from middlewares.middlewares import _user_in_all_channels
        ok = await _user_in_all_channels(call.bot, user_id, channels)
        if not ok:
            return await call.answer("🚫 Rejoins tous les canaux d'abord !", show_alert=True)
        await call.message.answer("✅ Vérification réussie ! Bienvenue 🎉", reply_markup=main_keyboard(user_id))
        await call.answer()
