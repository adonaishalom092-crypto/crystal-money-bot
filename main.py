import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ParseMode

# Récupération du token depuis les variables d'environnement
API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Username de ton canal public
CHANNEL_USERNAME = "@crystalmoneychannel"

# Commande /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id

    try:
        # Vérifier si l'utilisateur est membre du canal
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)

        if member.status in ["member", "creator", "administrator"]:
            # L'utilisateur est dans le canal
            await message.answer(f"✅ Bienvenue {message.from_user.first_name} ! Vous pouvez utiliser le bot.")
        else:
            # L'utilisateur n'est pas membre
            await message.answer(
                f"🚫 Rejoins le canal pour continuer:\n{CHANNEL_USERNAME}"
            )
    except:
        # Si l'utilisateur n'est pas membre ou autre erreur
        await message.answer(
            f"🚫 Rejoins le canal pour continuer:\n{CHANNEL_USERNAME}"
        )

# Message de bienvenue générique si nécessaire
@dp.message_handler()
async def echo(message: types.Message):
    await message.reply("Envie de commencer ? Tape /start pour vérifier l'accès au canal.")

if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
