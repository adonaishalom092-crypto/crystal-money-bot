from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
import asyncio

API_TOKEN = "TON_TOKEN_ICI"
CHANNEL_USERNAME = "@crystalmoneychannel"

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

pending_users = set()

async def check_membership(user_id: int):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status not in ['left', 'kicked']
    except Exception as e:
        print(f"Erreur vérification membre: {e}")
        return False

def join_button():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ J’ai rejoint", callback_data="joined_channel"))
    return keyboard

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    await message.reply("🤖 Bot démarré... Vérification du canal en cours.")
    
    is_member = await check_membership(user_id)
    if is_member:
        await message.reply(f"✅ Bonjour {message.from_user.first_name} ! Bienvenue dans le bot.")
    else:
        await message.reply(
            "🚫 Rejoins le canal pour continuer:\n"
            f"https://t.me/{CHANNEL_USERNAME[1:]}\n\n"
            "Puis clique sur le bouton ci-dessous après l'avoir rejoint.",
            reply_markup=join_button()
        )
        pending_users.add(user_id)

@dp.callback_query_handler(lambda c: c.data == "joined_channel")
async def joined_channel(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in pending_users:
        await callback_query.answer("Vous êtes déjà actif !", show_alert=True)
        return

    is_member = await check_membership(user_id)
    if is_member:
        await bot.send_message(user_id, f"✅ Merci {callback_query.from_user.first_name}, vous avez maintenant accès au bot !")
        pending_users.remove(user_id)
        await callback_query.answer("Accès validé !", show_alert=True)
    else:
        await callback_query.answer(
            "🚫 Vous n'avez pas encore rejoint le canal. Vérifie et clique à nouveau !",
            show_alert=True
        )

if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)  # skip_updates=True = ignore anciens messages
