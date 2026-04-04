import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

# Récupération du token depuis les variables d'environnement Railway
API_TOKEN = os.environ.get("API_TOKEN")

# Initialisation du bot
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# Création des boutons principaux
keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(KeyboardButton("🎁 Bonus"))
keyboard.add(KeyboardButton("👥 Parrainage"))
keyboard.add(KeyboardButton("💰 Solde"))
keyboard.add(KeyboardButton("💸 Retrait"))

# Message de bienvenue
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

# Messages détaillés
BONUS_MESSAGE = """
🎁 BONUS QUOTIDIEN

Félicitations ! Tu as reçu :
+25 FCFA 💰

⏳ Reviens demain pour réclamer encore plus !
"""

REFERRAL_MESSAGE = """
👥 TON LIEN D’AFFILIATION :

Invite tes amis et gagne 75 FCFA par personne active !

🔗 Ton lien :
https://t.me/Wellcashgain_bot?start=ID

💡 Plus tu invites, plus tu gagnes !
"""

BALANCE_MESSAGE = """
💰 TON SOLDE :

Montant actuel : XXX FCFA

💸 Minimum de retrait : 500 FCFA
"""

WITHDRAW_MESSAGE = """
💸 RETRAIT

Minimum : 500 FCFA

Choisis ton mode de paiement :

1️⃣ MTN Money
2️⃣ Orange Money
3️⃣ Wave
4️⃣ Autre (manuel)

Entre ton numéro après sélection et nom du bénéficiaire
"""

CONFIRMATION_MESSAGE = """
✅ DEMANDE ENREGISTRÉE

Ton retrait est en cours de traitement.

⏳ Délai : 24 à 48h

Merci pour ta confiance 🙏
"""

# Gestionnaire de démarrage
@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.answer(WELCOME_MESSAGE, reply_markup=keyboard)

# Gestion des boutons
@dp.message_handler(lambda message: message.text == "🎁 Bonus")
async def bonus(message: types.Message):
    await message.answer(BONUS_MESSAGE)

@dp.message_handler(lambda message: message.text == "👥 Parrainage")
async def referral(message: types.Message):
    await message.answer(REFERRAL_MESSAGE)

@dp.message_handler(lambda message: message.text == "💰 Solde")
async def balance(message: types.Message):
    await message.answer(BALANCE_MESSAGE)

@dp.message_handler(lambda message: message.text == "💸 Retrait")
async def withdraw(message: types.Message):
    await message.answer(WITHDRAW_MESSAGE)

# Exemple de confirmation de retrait
@dp.message_handler(lambda message: "paiement" in message.text.lower() or message.text.isdigit())
async def confirm_withdraw(message: types.Message):
    await message.answer(CONFIRMATION_MESSAGE)

if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
