# main.py
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.enums import ParseMode
import os

# ---------- CONFIGURATION ----------
API_TOKEN = os.environ.get("API_TOKEN")  # Définie dans Railway
OWNER_ID = int(os.environ.get("OWNER_ID"))  # ID Telegram admin dans Railway

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# ---------- BASE DE DONNÉES ----------
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    username TEXT,
    balance INTEGER DEFAULT 0,
    referrer_id INTEGER,
    last_bonus_date TEXT,
    total_referrals INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------- MESSAGES ----------
ONBOARDING_TEXT = """
<b>💎 Que peut faire ce bot ?</b>

Bienvenue sur <b>CRYSTAL MONEY BOT</b> !

Ce bot vous permet de gagner de l'argent en parrainant des amis et en réclamant des bonus quotidiens.

🔥 <b>Comment ça marche ?</b>

🎁 25 FCFA bonus quotidien  
👥 75 FCFA par parrainage

💸 Retrait minimum : 500 FCFA  
📲 Modes : MTN / MOOV / Orange Money / Wave
"""

WELCOME_TEXT = """
Cher <b>{username}</b> 💥

Bienvenue sur notre plateforme de gains !

💸 Gagne de l’argent facilement et légalement chaque jour :

✅ 25 FCFA chaque matin (bonus quotidien)  
✅ 75 FCFA par invitation qui réclame son bonus  

🚨 <b>IMPORTANT :</b>  
Tu dois rejoindre notre canal officiel 👇

👉 https://t.me/crystalmoneychannel  

Une fois rejoint, clique sur <b>✅ Vérifier</b> pour commencer.
"""

# ---------- CLAVIERS ----------
def channel_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔘 Rejoindre le canal", url="https://t.me/crystalmoneychannel"))
    kb.add(InlineKeyboardButton("✅ Vérifier", callback_data="check"))
    return kb

def main_buttons():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🎁 Bonus", callback_data="bonus"),
        InlineKeyboardButton("👥 Parrainage", callback_data="referral"),
        InlineKeyboardButton("💰 Solde", callback_data="balance"),
        InlineKeyboardButton("💸 Retrait", callback_data="withdraw")
    )
    return kb

def admin_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin"))
    return kb

# ---------- HANDLERS ----------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.first_name

    # Vérifie si utilisateur existe
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        conn.commit()

    # Message de bienvenue
    text = WELCOME_TEXT.format(username=username)

    # Ajouter bouton Admin si propriétaire
    if user_id == OWNER_ID:
        await message.answer(text, reply_markup=admin_keyboard())
    else:
        await message.answer(text, reply_markup=channel_keyboard())

# ---------- CALLBACK HANDLERS ----------
@dp.callback_query_handler(lambda c: c.data == "check")
async def check_channel(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    # Ici tu peux vérifier si l'utilisateur a rejoint le canal via Telegram API
    # Pour l'instant on considère que l'utilisateur a rejoint
    await callback_query.message.edit_text(
        "✅ Vérification réussie ! Tu peux maintenant utiliser le bot.", 
        reply_markup=main_buttons()
    )

@dp.callback_query_handler(lambda c: c.data == "bonus")
async def daily_bonus(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    today = datetime.today().date()

    cursor.execute("SELECT balance, last_bonus_date, referrer_id FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        await callback_query.answer("Erreur : utilisateur non trouvé !")
        return

    balance, last_bonus_date, referrer_id = user

    if last_bonus_date != str(today):
        balance += 25
        cursor.execute(
            "UPDATE users SET balance=?, last_bonus_date=? WHERE user_id=?",
            (balance, str(today), user_id)
        )
        conn.commit()

        # Ajouter bonus au parrain si actif
        if referrer_id:
            cursor.execute("SELECT balance FROM users WHERE id=?", (referrer_id,))
            ref = cursor.fetchone()
            if ref:
                ref_balance = ref[0] + 75
                cursor.execute("UPDATE users SET balance=? WHERE id=?", (ref_balance, referrer_id))
                conn.commit()

        await callback_query.answer("🎁 Bonus quotidien reçu : 25 FCFA")
    else:
        await callback_query.answer("⏳ Déjà réclamé aujourd'hui ! Reviens demain.")

@dp.callback_query_handler(lambda c: c.data == "referral")
async def referral(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    link = f"https://t.me/Wellcashgain_bot?start={user_id}"
    await callback_query.message.answer(
        f"👥 Ton lien d’affiliation :\n\n{link}\n\n💡 Plus tu invites, plus tu gagnes !"
    )

@dp.callback_query_handler(lambda c: c.data == "balance")
async def balance(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if user:
        balance = user[0]
        await callback_query.message.answer(f"💰 Ton solde actuel : {balance} FCFA\n💸 Minimum de retrait : 500 FCFA")
    else:
        await callback_query.message.answer("Erreur : utilisateur non trouvé.")

@dp.callback_query_handler(lambda c: c.data == "withdraw")
async def withdraw(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if user and user[0] >= 500:
        await callback_query.message.answer("💸 Retrait en cours. Merci de patienter 24-48h.")
        # Soustraire balance si besoin
    else:
        await callback_query.message.answer("⚠️ Solde insuffisant pour retrait (minimum 500 FCFA).")

@dp.callback_query_handler(lambda c: c.data == "admin")
async def admin_panel(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("❌ Accès refusé")
        return
    await callback_query.message.answer("⚙️ Bienvenue dans le panneau admin !")

# ---------- RUN ----------
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
