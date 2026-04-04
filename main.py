import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ParseMode

# Token depuis les variables d'environnement
API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Username de ton canal public
CHANNEL_USERNAME = "@crystalmoneychannel"

# Message de bienvenue complet
WELCOME_MESSAGE = """
💎 Bienvenue sur Crystal Money Bot

🔥 Gagne facilement et légalement du FCFA chaque jour !

💰 Ce que tu gagnes :
🎁 Bonus quotidien : 25 FCFA
👥 Parrainage : 75 FCFA par personne

🚀 Retrait à partir de 500 FCFA

📲 Paiement rapide via :
- MTN Money
- Orange Money
- Wave
- Moov Money

⚠️ Rejoins le canal obligatoire pour activer ton compte :
@crystalmoneychannel
"""

# Commande /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id

    # Envoi du message de bienvenue
    await message.answer(WELCOME_MESSAGE)

    # Vérifier si l'utilisateur est membre du canal
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "creator", "administrator"]:
            await message.answer("✅ Ton compte est activé ! Tu peux utiliser le bot.")
        else:
            await message.answer(f"🚫 Rejoins le canal pour continuer : {CHANNEL_USERNAME}")
    except:
        await message.answer(f"🚫 Rejoins le canal pour continuer : {CHANNEL_USERNAME}")

# Pour tout autre message
@dp.message_handler()
async def echo(message: types.Message):
    await message.reply("Tape /start pour voir le message de bienvenue et activer ton compte.")

if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
