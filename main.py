from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ParseMode
import asyncio

API_TOKEN = "TON_TOKEN_ICI"
CHANNEL_USERNAME = "@crystalmoneychannel"  # Username public du canal

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Stockage temporaire des utilisateurs en attente
pending_users = set()

async def check_membership(user_id: int):
    """
    Vérifie si l'utilisateur est membre du canal public
    """
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status not in ['left', 'kicked']
    except Exception as e:
        print(f"Erreur vérification membre: {e}")
        return False

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    is_member = await check_membership(message.from_user.id)
    if is_member:
        await message.reply(f"✅ Bonjour {message.from_user.first_name} ! Bienvenue dans le bot.")
    else:
        await message.reply(
            "🚫 Rejoins le canal pour continuer:\n"
            f"https://t.me/{CHANNEL_USERNAME[1:]}\n\n"
            "Puis renvoie /start après l'avoir rejoint."
        )
        # Ajout de l'utilisateur à la liste d'attente
        pending_users.add(message.from_user.id)

@dp.message_handler(commands=['check'])
async def check(message: types.Message):
    """
    Commande pour que l'utilisateur vérifie son statut après avoir rejoint le canal
    """
    if message.from_user.id not in pending_users:
        await message.reply("Vous n'avez pas besoin de vérifier, vous êtes déjà actif.")
        return

    is_member = await check_membership(message.from_user.id)
    if is_member:
        await message.reply(f"✅ Merci {message.from_user.first_name}, vous avez maintenant accès au bot !")
        pending_users.remove(message.from_user.id)
    else:
        await message.reply(
            "🚫 Vous n'avez pas encore rejoint le canal.\n"
            f"Rejoins ici: https://t.me/{CHANNEL_USERNAME[1:]}"
        )

if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=False)
