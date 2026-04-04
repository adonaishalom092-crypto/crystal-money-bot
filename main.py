from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import datetime
import os

# ⚠️ Le TOKEN et l'ID admin doivent être configurés dans Railway Variables
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CHANNEL_USERNAME = "@crystalmoneychannel"

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Base de données simple simulée
USERS = {}  # {user_id: {"balance": 0, "last_bonus": None, "referrer": None}}

# --- CLAVIER PRINCIPAL ---
def main_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎁 Bonus", callback_data="daily_bonus"),
        InlineKeyboardButton("👥 Parrainage", callback_data="referral")
    )
    keyboard.add(
        InlineKeyboardButton("💰 Solde", callback_data="balance")
    )
    keyboard.add(
        InlineKeyboardButton("💸 Retrait", callback_data="withdraw")
    )
    return keyboard

# --- CLAVIER VERIFICATION ---
def verification_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔘 Rejoindre le canal", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"),
        InlineKeyboardButton("🔘 Vérifier", callback_data="check_membership")
    )
    return keyboard

# --- MESSAGE DE BIENVENUE ---
WELCOME_MESSAGE = f"""
💎 Bienvenue sur Crystal Money Bot

🔥 Gagne facilement et légalement du FCFA chaque jour !

💰 Ce que tu gagnes :
🎁 Bonus quotidien : 25 FCFA
👥 Parrainage : 75 FCFA par personne

     🚨
🚀 Retrait à partir de 500 FCFA

📲 Paiement rapide via :
- MTN Money
- Orange Money
- Wave
- Moov Money
          
         🚨 IMPORTANT :
Pour continuer, tu dois rejoindre notre canal officiel 👇

👉 [{CHANNEL_USERNAME}]

Une fois rejoint, clique sur "✅ Vérifier" pour commencer.
"""

# --- START ---
@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if user_id not in USERS:
        USERS[user_id] = {"balance": 0, "last_bonus": None, "referrer": None}
    await message.answer(WELCOME_MESSAGE, reply_markup=verification_keyboard())

# --- VERIFICATION DU CANAL ---
@dp.callback_query_handler(lambda c: c.data == "check_membership")
async def check_membership(call: types.CallbackQuery):
    user_id = call.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ["member", "creator", "administrator"]:
            await call.message.answer("✅ Vérification réussie ! Voici ton menu principal :", reply_markup=main_keyboard())
        else:
            await call.answer("🚫 Tu dois rejoindre le canal pour continuer.", show_alert=True)
    except:
        await call.answer("🚫 Impossible de vérifier le canal. Rejoins-le d'abord !", show_alert=True)

# --- GESTION DES BOUTONS ---
@dp.callback_query_handler(lambda c: c.data in ["daily_bonus", "referral", "balance", "withdraw"])
async def handle_buttons(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = USERS.get(user_id)
    if not user:
        USERS[user_id] = {"balance": 0, "last_bonus": None, "referrer": None}
        user = USERS[user_id]

    if call.data == "daily_bonus":
        today = datetime.date.today()
        if user["last_bonus"] != today:
            user["balance"] += 25
            user["last_bonus"] = today

            # Parrainage automatique pour le premier bonus
            if user["referrer"]:
                referrer = USERS.get(user["referrer"])
                if referrer:
                    referrer["balance"] += 75

            await call.message.answer("🎁 BONUS QUOTIDIEN\n\nFélicitations ! Tu as reçu : +25 FCFA 💰\n⏳ Reviens demain pour réclamer encore plus !")
        else:
            await call.answer("❌ Déjà réclamé aujourd'hui.", show_alert=True)

    elif call.data == "referral":
        link = f"https://t.me/{bot.username}?start={user_id}"
        await call.message.answer(f"👥 TON LIEN D’AFFILIATION :\n\nInvite tes amis et gagne 75 FCFA par personne active !\n\n🔗 Ton lien : {link}\n\n💡 Plus tu invites, plus tu gagnes !")

    elif call.data == "balance":
        await call.message.answer(f"💰 TON SOLDE :\n\nMontant actuel : {user['balance']} FCFA\n💸 Minimum de retrait : 500 FCFA")

    elif call.data == "withdraw":
        if user["balance"] >= 500:
            user["balance"] -= 500  # On simule le retrait
            await call.message.answer("✅ DEMANDE ENREGISTRÉE\n\nTon retrait est en cours de traitement.\n⏳ Délai : 24 à 48h\nMerci pour ta confiance 🙏")
        else:
            await call.message.answer("❌ Solde insuffisant pour le retrait. Minimum 500 FCFA.")

# --- RUN ---
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
