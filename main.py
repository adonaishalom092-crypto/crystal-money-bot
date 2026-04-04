from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from datetime import datetime
import os

# --- Configuration ---
API_TOKEN = os.getenv("API_TOKEN")  # Token du bot depuis Railway
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # ID admin depuis Railway
CHANNEL_USERNAME = "@crystalmoneychannel"  # Ton canal public

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# --- Base simulée (à remplacer par une vraie BDD plus tard) ---
USERS = {}  # user_id: {balance, referrer_id, last_bonus_date, total_referrals}

# --- Clavier fixe ---
user_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
user_keyboard.row(
    KeyboardButton("🎁 Bonus"), KeyboardButton("👥 Parrainage")
)
user_keyboard.row(
    KeyboardButton("💰 Solde")
)
user_keyboard.row(
    KeyboardButton("💸 Retrait")
)
# ligne vide pour pousser le clavier vers le bas
user_keyboard.row(
    KeyboardButton(" "), KeyboardButton(" ")
)
user_keyboard.row(
    KeyboardButton("🔘 Rejoindre le canal"), KeyboardButton("✅ Vérifier")
)

# --- Messages ---
WELCOME_TEXT = """
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
          
🚨 IMPORTANT :
Pour continuer, tu dois rejoindre notre canal officiel 👇

👉 [@crystalmoneychannel]

Une fois rejoint, clique sur "✅ Vérifier" pour commencer.
"""

# --- Helpers ---
def get_user(user_id):
    if user_id not in USERS:
        USERS[user_id] = {"balance": 0, "referrer_id": None, "last_bonus_date": None, "total_referrals": 0}
    return USERS[user_id]

def is_joined_channel(member):
    # ici, on vérifie si l'utilisateur a rejoint le canal
    return member  # True/False (à remplacer par vérification réelle Telegram API)

# --- Handlers ---
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(WELCOME_TEXT, reply_markup=user_keyboard)

@dp.message_handler(lambda m: m.text == "🔘 Rejoindre le canal")
async def join_channel(message: types.Message):
    await message.answer(f"Rejoins le canal ici : {CHANNEL_USERNAME}")

@dp.message_handler(lambda m: m.text == "✅ Vérifier")
async def verify_channel(message: types.Message):
    # Exemple simple, ici tu peux faire une vraie vérification avec get_chat_member
    member = True  # Simulé pour test
    if member:
        await message.answer("✅ Vérification réussie ! Tu peux maintenant utiliser le bot.")
    else:
        await message.answer("🚫 Tu dois rejoindre le canal pour continuer !")

@dp.message_handler(lambda m: m.text == "🎁 Bonus")
async def bonus(message: types.Message):
    user = get_user(message.from_user.id)
    today = datetime.now().date()
    if user["last_bonus_date"] != today:
        user["balance"] += 25
        user["last_bonus_date"] = today
        await message.answer("🎁 BONUS QUOTIDIEN\n\nFélicitations ! Tu as reçu : +25 FCFA 💰\n⏳ Reviens demain pour réclamer encore plus !")
        # Bonus parrainage si referrer
        ref_id = user.get("referrer_id")
        if ref_id and ref_id in USERS:
            USERS[ref_id]["balance"] += 75
    else:
        await message.answer("⏳ Tu as déjà réclamé ton bonus aujourd'hui.")

@dp.message_handler(lambda m: m.text == "👥 Parrainage")
async def referral(message: types.Message):
    user_id = message.from_user.id
    link = f"https://t.me/Wellcashgain_bot?start={user_id}"
    await message.answer(f"👥 TON LIEN D’AFFILIATION :\n\nInvite tes amis et gagne 75 FCFA par personne active !\n\n🔗 Ton lien : {link}\n\n💡 Plus tu invites, plus tu gagnes !")

@dp.message_handler(lambda m: m.text == "💰 Solde")
async def balance(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(f"💰 TON SOLDE :\n\nMontant actuel : {user['balance']} FCFA\n💸 Minimum de retrait : 500 FCFA")

@dp.message_handler(lambda m: m.text == "💸 Retrait")
async def withdrawal(message: types.Message):
    user = get_user(message.from_user.id)
    if user["balance"] >= 500:
        await message.answer("💸 RETRAIT\n\nMinimum : 500 FCFA\nChoisis ton mode de paiement :\n1️⃣ MTN Money\n2️⃣ Orange Money\n3️⃣ Wave\n4️⃣ Autre (manuel)\n\nEntre ton numéro après sélection et nom du bénéficiaire")
    else:
        await message.answer("❌ Solde insuffisant pour le retrait. Minimum : 500 FCFA")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    # Ajoute ici les boutons spéciaux pour le propriétaire
    pass

# --- Run bot ---
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
