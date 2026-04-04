import os
from datetime import date
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

# API Token depuis Railway
API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# --- Messages ---
WELCOME_MESSAGE = """💎 Bienvenue sur Crystal Money Bot

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

BONUS_MESSAGE = """🎁 BONUS QUOTIDIEN

Félicitations ! Tu as reçu :
+25 FCFA 💰

⏳ Reviens demain pour réclamer encore plus !
"""

ALREADY_CLAIMED_MESSAGE = "⏳ Tu as déjà réclamé ton bonus aujourd'hui. Reviens demain !"

REFERRAL_MESSAGE = """👥 TON LIEN D’AFFILIATION :

Invite tes amis et gagne 75 FCFA par personne active !

🔗 Ton lien :
https://t.me/Wellcashgain_bot?start={user_id}

💡 Plus tu invites, plus tu gagnes !
"""

BALANCE_MESSAGE = """💰 TON SOLDE :

Montant actuel : {balance} FCFA

💸 Minimum de retrait : 500 FCFA
"""

WITHDRAW_MESSAGE = """💸 RETRAIT

Minimum : 500 FCFA

Choisis ton mode de paiement :
1️⃣ MTN Money
2️⃣ Orange Money
3️⃣ Wave
4️⃣ Autre (manuel)

Entre ton numéro après sélection et nom du bénéficiaire
"""

CONFIRM_WITHDRAW_MESSAGE = """✅ DEMANDE ENREGISTRÉE

Ton retrait est en cours de traitement.

⏳ Délai : 24 à 48h

Merci pour ta confiance 🙏
"""

# --- Boutons ---
keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(KeyboardButton("🎁 Bonus"))
keyboard.add(KeyboardButton("👥 Parrainage"))
keyboard.add(KeyboardButton("💰 Solde"))
keyboard.add(KeyboardButton("💸 Retrait"))

# --- Base de données simple en mémoire ---
# Dans une vraie version, remplacer par SQLite / PostgreSQL
USERS = {}  # user_id: dict(balance, referrer_id, last_bonus_date, total_referrals)

def get_or_create_user(user_id, referrer_id=None):
    if user_id not in USERS:
        USERS[user_id] = {
            "balance": 0,
            "referrer_id": referrer_id,
            "last_bonus_date": None,
            "total_referrals": 0
        }
    return USERS[user_id]

# --- Vérification abonnement au canal ---
async def enforce_subscription(message: types.Message):
    chat_member = await bot.get_chat_member("@crystalmoneychannel", message.from_user.id)
    if chat_member.status in ["left", "kicked"]:
        await message.answer("🚫 Rejoins le canal pour continuer:\nhttps://t.me/+RBJns9gbyWdiYWYy")
        return False
    return True

# --- Handlers ---
@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.answer(WELCOME_MESSAGE, reply_markup=keyboard)
    referrer_id = None
    if "start" in message.get_args():
        try:
            referrer_id = int(message.get_args())
        except ValueError:
            pass
    get_or_create_user(message.from_user.id, referrer_id=referrer_id)

@dp.message_handler(lambda message: message.text == "🎁 Bonus")
async def handle_bonus(message: types.Message):
    if not await enforce_subscription(message):
        return

    user = get_or_create_user(message.from_user.id)
    today_str = date.today().isoformat()

    if user["last_bonus_date"] != today_str:
        # Bonus quotidien
        user["balance"] += 25
        user["last_bonus_date"] = today_str
        await message.answer(BONUS_MESSAGE)

        # Bonus parrainage au premier bonus
        referrer_id = user["referrer_id"]
        if referrer_id and referrer_id in USERS:
            referrer = USERS[referrer_id]
            referrer["balance"] += 75
            referrer["total_referrals"] += 1
            await bot.send_message(referrer_id,
                                   f"🎉 Bravo ! Ton filleul {message.from_user.full_name} a réclamé son premier bonus. Tu gagnes +75 FCFA !")
    else:
        await message.answer(ALREADY_CLAIMED_MESSAGE)

@dp.message_handler(lambda message: message.text == "👥 Parrainage")
async def handle_referral(message: types.Message):
    user = get_or_create_user(message.from_user.id)
    await message.answer(REFERRAL_MESSAGE.format(user_id=message.from_user.id))

@dp.message_handler(lambda message: message.text == "💰 Solde")
async def handle_balance(message: types.Message):
    user = get_or_create_user(message.from_user.id)
    await message.answer(BALANCE_MESSAGE.format(balance=user["balance"]))

@dp.message_handler(lambda message: message.text == "💸 Retrait")
async def handle_withdraw(message: types.Message):
    user = get_or_create_user(message.from_user.id)
    if user["balance"] < 500:
        await message.answer(f"❌ Solde insuffisant pour un retrait.\nMontant actuel : {user['balance']} FCFA\nMinimum : 500 FCFA")
        return
    await message.answer(WITHDRAW_MESSAGE)

# --- Démarrage ---
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
